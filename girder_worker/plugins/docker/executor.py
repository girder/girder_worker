import os
import re
import subprocess

from girder_worker import logger
from girder_worker.core import TaskSpecValidationError, utils
from girder_worker.core.io import make_stream_fetch_adapter, make_stream_push_adapter

DATA_VOLUME = '/mnt/girder_worker/data'


def _pull_image(image):
    """
    Pulls the specified Docker image onto this worker.
    """
    command = ('docker', 'pull', image)
    p = subprocess.Popen(args=command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()

    if p.returncode != 0:
        logger.error(
            'Error pulling Docker image %s:\nSTDOUT: %s\nSTDERR: %s', image, stdout, stderr)

        raise Exception('Docker pull returned code {}.'.format(p.returncode))


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

        if arg:
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


def _setup_pipes(task_inputs, inputs, task_outputs, outputs, tempdir):
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
        if (spec.get('stream') and id in bindings and
                spec.get('target') == 'filepath'):
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

    # special handling for stdin, stdout, and stderr pipes
    if '_stdin' in task_inputs and '_stdin' in inputs:
        if task_inputs['_stdin'].get('stream'):
            ipipes['_stdin'] = make_stream_fetch_adapter(inputs['_stdin'])
        else:
            ipipes['_stdin'] = utils.MemoryFetchAdapter(
                inputs[id], inputs[id]['data'])

    for id in ('_stdout', '_stderr'):
        if id in task_outputs and id in outputs:
            if task_outputs[id].get('stream'):
                opipes[id] = make_stream_push_adapter(outputs[id])
            else:
                opipes[id] = utils.AccumulateDictAdapter(
                    outputs[id], 'script_data')

    return ipipes, opipes


def run(task, inputs, outputs, task_inputs, task_outputs, **kwargs):
    image = task['docker_image']

    if task.get('pull_image', True):
        logger.info('Pulling Docker image: %s', image)
        _pull_image(image)

    tempdir = kwargs.get('_tempdir')
    args = _expand_args(task.get('container_args', []), inputs, task_inputs, tempdir)

    ipipes, opipes = _setup_pipes(
        task_inputs, inputs, task_outputs, outputs, tempdir)

    if 'entrypoint' in task:
        if isinstance(task['entrypoint'], (list, tuple)):
            ep_args = ['--entrypoint'] + task['entrypoint']
        else:
            ep_args = ['--entrypoint', task['entrypoint']]
    else:
        ep_args = []

    command = [
        'docker', 'run',
        '-v', '%s:%s' % (tempdir, DATA_VOLUME)
    ] + task.get('docker_run_args', []) + ep_args + [image] + args

    logger.info('Running container: %s', repr(command))

    p = utils.run_process(command, output_pipes=opipes, input_pipes=ipipes)

    if p.returncode != 0:
        raise Exception('Error: docker run returned code %d.' % p.returncode)

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
