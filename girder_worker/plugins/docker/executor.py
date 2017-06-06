import os
import re
import sys
import docker
from docker.errors import DockerException

from girder_worker import logger
from girder_worker.core import TaskSpecValidationError, utils
from girder_worker.core.io import make_stream_fetch_adapter, make_stream_push_adapter
from girder_worker.plugins.docker.stream_adapter import DockerStreamPushAdapter
from . import nvidia

DATA_VOLUME = '/mnt/girder_worker/data'
BLACKLISTED_DOCKER_RUN_ARGS = ['tty', 'detach']


def _pull_image(image):
    """
    Pulls the specified Docker image onto this worker.
    """
    client = docker.from_env(version='auto')
    try:
        client.images.pull(image)
    except DockerException as dex:
        logger.error('Error pulling Docker image %s:' % image)
        logger.exception(dex)
        raise


def _transform_path(inputs, taskInputs, inputId, tmpDir):
    """
    If the input specified by inputId is a filepath target, we transform it to
    its absolute path within the Docker container (underneath the data mount).
    """
    for ti in taskInputs.itervalues():
        tiId = ti['id'] if 'id' in ti else ti['name']
        if tiId == inputId:
            if ti.get('target') == 'filepath':
                rel = os.path.relpath(inputs[inputId]['script_data'], tmpDir)
                return os.path.join(DATA_VOLUME, rel)
            else:
                return inputs[inputId]['script_data']

    raise Exception('No task input found with id = ' + inputId)


def _expand_args(args, inputs, taskInputs, tmpDir):
    """
    Expands arguments to the container execution if they reference input
    data. For example, if an input has id=foo, then a container arg of the form
    $input{foo} would be expanded to the runtime value of that input. If that
    input is a filepath target, the file path will be transformed into the
    location that it will be available inside the running container.
    """
    newArgs = []
    inputRe = re.compile(r'\$input\{([^}]+)\}')
    flagRe = re.compile(r'\$flag\{([^}]+)\}')

    for arg in args:
        skip = False
        for inputId in re.findall(inputRe, arg):
            if inputId in inputs:
                transformed = _transform_path(
                    inputs, taskInputs, inputId, tmpDir)
                arg = arg.replace('$input{%s}' % inputId, str(transformed))
            elif inputId == '_tempdir':
                arg = arg.replace('$input{_tempdir}', DATA_VOLUME)
        for inputId in re.findall(flagRe, arg):
            if inputId in inputs and inputs[inputId]['script_data']:
                val = taskInputs[inputId].get('arg', inputId)
            else:
                val = ''
            arg = arg.replace('$flag{%s}' % inputId, val)
            if not arg:
                skip = True
        if not skip:
            newArgs.append(arg)

    return newArgs


def validate_task_outputs(task_outputs):
    """
    This is called prior to fetching inputs to make sure the output specs are
    valid. Outputs in docker mode can result in side effects, so it's best to
    make sure the specs are valid prior to fetching.
    """
    for name, spec in task_outputs.iteritems():
        if spec.get('target') == 'filepath':
            path = spec.get('path', name)
            if path.startswith('/') and not path.startswith(DATA_VOLUME + '/'):
                raise TaskSpecValidationError(
                    'Docker filepath output paths must either start with '
                    '"%s/" or be specified relative to that directory.' %
                    DATA_VOLUME)
        elif name not in ('_stdout', '_stderr'):
            raise TaskSpecValidationError(
                'Docker outputs must be either "_stdout", "_stderr", or '
                'filepath-target outputs.')


def _setup_pipes(task_inputs, inputs, task_outputs, outputs, tempdir, job_mgr, progress_pipe):
    """
    Returns a 2 tuple of input and output pipe mappings. The first element is
    a dict mapping input file descriptors to the corresponding stream adapters,
    the second is a dict mapping output file descriptors to the corresponding
    stream adapters. This also handles the special cases of STDIN, STDOUT, and
    STDERR mappings, and in the case of non-streaming standard IO pipes, will
    create default bindings for those as well.
    """
    ipipes = {}
    opipes = {}

    def make_pipe(id, spec, bindings):
        """
        Helper to make a pipe conditionally for valid streaming IO specs. If the
        given spec is not a streaming spec, returns False. If it is, returns the
        path to the pipe file that was created.
        """
        if spec.get('stream') and id in bindings and spec.get('target') == 'filepath':
            path = spec.get('path', id)
            if path.startswith('/'):
                raise Exception('Streaming filepaths must be relative.')
            path = os.path.join(tempdir, path)
            os.mkfifo(path)
            return path
        return False

    # handle stream inputs
    for id, spec in task_inputs.iteritems():
        pipe = make_pipe(id, spec, inputs)
        if pipe:
            # Don't open from this side, must be opened for reading first!
            ipipes[pipe] = make_stream_fetch_adapter(inputs[id])

    # handle stream outputs
    for id, spec in task_outputs.iteritems():
        pipe = make_pipe(id, spec, outputs)
        if pipe:
            opipes[os.open(pipe, os.O_RDONLY | os.O_NONBLOCK)] = \
                make_stream_push_adapter(outputs[id])

    # handle special stream output for job progress
    if progress_pipe and job_mgr:
        path = os.path.join(tempdir, '.girder_progress')
        os.mkfifo(path)
        opipes[os.open(path, os.O_RDONLY | os.O_NONBLOCK)] = utils.JobProgressAdapter(job_mgr)

    # special handling for stdin, stdout, and stderr pipes
    if '_stdin' in task_inputs and '_stdin' in inputs:
        if task_inputs['_stdin'].get('stream'):
            ipipes['_stdin'] = make_stream_fetch_adapter(inputs['_stdin'])
        else:
            ipipes['_stdin'] = utils.MemoryFetchAdapter(inputs[id], inputs[id]['data'])

    for id in ('_stdout', '_stderr'):
        if id in task_outputs and id in outputs:
            if task_outputs[id].get('stream'):
                opipes[id] = make_stream_push_adapter(outputs[id])
            else:
                opipes[id] = utils.AccumulateDictAdapter(outputs[id], 'script_data')

    return ipipes, opipes


def _run_container(image, args, **kwargs):
    # TODO we could allow configuration of non default socket
    client = docker.from_env(version='auto')
    if nvidia.is_nvidia_image(client.api, image):
        client = nvidia.NvidiaDockerClient.from_env(version='auto')

    logger.info('Running container: image: %s args: %s kwargs: %s' % (image, args, kwargs))
    try:
        return client.containers.run(image, args, **kwargs)
    except DockerException as dex:
        logger.error(dex)
        raise


def _run_select_loop(container, opipes, ipipes):
    stdout = None
    stderr = None
    try:
        # attach to standard streams
        stdout = container.attach_socket(params={
            'stdout': True,
            'logs': True,
            'stream': True
        })

        stderr = container.attach_socket(params={
            'stderr': True,
            'logs': True,
            'stream': True
        })

        def exit_condition():
            container.reload()
            return container.status in ['exited', 'dead']

        def close_output(output):
            return output not in (stdout.fileno(), stderr.fileno())

        opipes[stdout.fileno()] = DockerStreamPushAdapter(opipes.get(
            '_stdout', utils.WritePipeAdapter({}, sys.stdout)))
        opipes[stderr.fileno()] = DockerStreamPushAdapter(opipes.get(
            '_stderr', utils.WritePipeAdapter({}, sys.stderr)))

        # Run select loop
        utils.select_loop(exit_condition=exit_condition, close_output=close_output,
                          outputs=opipes, inputs=ipipes)
    finally:
        # Close our stdout and stderr sockets
        if stdout:
            stdout.close()
        if stderr:
            stderr.close()


def run(task, inputs, outputs, task_inputs, task_outputs, **kwargs):
    image = task['docker_image']

    if task.get('pull_image', True):
        logger.info('Pulling Docker image: %s', image)
        _pull_image(image)

    progress_pipe = task.get('progress_pipe', False)

    tempdir = kwargs.get('_tempdir')
    job_mgr = kwargs.get('_job_manager')
    args = _expand_args(task.get('container_args', []), inputs, task_inputs, tempdir)

    ipipes, opipes = _setup_pipes(
        task_inputs, inputs, task_outputs, outputs, tempdir, job_mgr, progress_pipe)

    if 'entrypoint' in task:
        if isinstance(task['entrypoint'], (list, tuple)):
            ep_args = task['entrypoint']
        else:
            ep_args = [task['entrypoint']]
    else:
        ep_args = []

    run_kwargs = {
        'tty': False,
        'volumes': {
            tempdir: {
                'bind': DATA_VOLUME,
                'mode': 'rw'
            }
        },
        'detach': True
    }

    if ep_args:
        run_kwargs['entrypoint'] = ep_args

    # Allow run args to overridden
    extra_run_kwargs = task.get('docker_run_args', {})
    # Filter out any we don't want to override
    extra_run_kwargs = {k: v for k, v in extra_run_kwargs.items() if k not
                        in BLACKLISTED_DOCKER_RUN_ARGS}
    run_kwargs.update(extra_run_kwargs)

    container = _run_container(image, args, **run_kwargs)

    try:
        _run_select_loop(container, opipes, ipipes)
    finally:
        if container and kwargs.get('_rm_container'):
            container.remove()

    for name, spec in task_outputs.iteritems():
        if spec.get('target') == 'filepath' and not spec.get('stream'):
            path = spec.get('path', name)
            if not path.startswith('/'):
                # Assume relative paths are relative to the data volume
                path = os.path.join(DATA_VOLUME, path)

            # Convert data volume refs to the temp dir on the host
            path = path.replace(DATA_VOLUME, tempdir, 1)
            if not os.path.exists(path):
                raise Exception('Output filepath %s does not exist.' % path)
            outputs[name]['script_data'] = path
