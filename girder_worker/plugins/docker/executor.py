import json
import os
import re
import subprocess

from girder_worker import config
from girder_worker.core import TaskSpecValidationError, utils
from girder_worker.core.io import (
    make_stream_fetch_adapter, make_stream_push_adapter)

DATA_VOLUME = '/mnt/girder_worker/data'
SCRIPTS_VOLUME = '/mnt/girder_worker/scripts'
SCRIPTS_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                           'scripts')


def _pull_image(image):
    """
    Pulls the specified Docker image onto this worker.
    """
    command = ('docker', 'pull', image)
    p = subprocess.Popen(args=command, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()

    if p.returncode != 0:
        print('Error pulling Docker image %s:' % image)
        print('STDOUT: ' + stdout)
        print('STDERR: ' + stderr)

        raise Exception('Docker pull returned code {}.'.format(p.returncode))


def _read_from_config(key, default):
    """
    Helper to read Docker specific config values from the worker config files.
    """
    if config.has_option('docker', key):
        return config.get('docker', key)
    else:
        return default


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
    regex = re.compile(r'\$input\{([^}]+)\}')

    for arg in args:
        for inputId in re.findall(regex, arg):
            if inputId in inputs:
                transformed = _transform_path(inputs, taskInputs, inputId,
                                              tmpDir)
                arg = arg.replace('$input{%s}' % inputId, transformed)
            elif inputId == '_tempdir':
                arg = arg.replace('$input{_tempdir}', DATA_VOLUME)

        newArgs.append(arg)

    return newArgs


def _docker_gc(tempdir):
    """
    Garbage collect containers that have not been run in the last hour using the
    https://github.com/spotify/docker-gc project's script, which is copied in
    the same directory as this file. After that, deletes all images that are
    no longer used by any containers.

    This starts the script in the background and returns the subprocess object.
    Waiting for the subprocess to complete is left to the caller, in case they
    wish to do something in parallel with the garbage collection.

    Standard output and standard error pipes from this subprocess are the same
    as the current process to avoid blocking on a full buffer.

    :param tempdir: Temporary directory where the GC should write files.
    :type tempdir: str
    :returns: The process object that was created.
    :rtype: `subprocess.Popen`
    """
    script = os.path.join(os.path.dirname(__file__), 'docker-gc')
    if not os.path.isfile(script):
        raise Exception('Docker GC script %s not found.' % script)
    if not os.access(script, os.X_OK):
        raise Exception('Docker GC script %s is not executable.' % script)

    env = os.environ.copy()
    env['FORCE_CONTAINER_REMOVAL'] = '1'
    env['STATE_DIR'] = tempdir
    env['PID_DIR'] = tempdir
    env['GRACE_PERIOD_SECONDS'] = str(_read_from_config('cache_timeout', 3600))

    # Handle excluded images
    excluded = _read_from_config('exclude_images', '').split(',')
    excluded = [img for img in excluded if img.strip()]
    if excluded:
        exclude_file = os.path.join(tempdir, '.docker-gc-exclude')
        with open(exclude_file, 'w') as fd:
            fd.write('\n'.join(excluded) + '\n')
        env['EXCLUDE_FROM_GC'] = exclude_file

    return subprocess.Popen(args=(script,), env=env)


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


def _get_pre_args(task, uid, gid):
    """
    When using our entrypoint.sh script, we have to detect the existing entry
    point and munge the args to make the behavior equivalent. This returns
    the list of arguments that should go prior to the client-specified args.
    """
    args = [str(uid), str(gid)]

    if 'entrypoint' in task:
        if isinstance(task['entrypoint'], (list, tuple)):
            args.extend(task['entrypoint'])
        else:
            args.append(task['entrypoint'])
    else:
        # Read entrypoint from container if default is used
        info = json.loads(subprocess.check_output(
            args=['docker', 'inspect', '--type=image', task['docker_image']]))
        args.extend(info[0]['Config']['Entrypoint'])

    return args


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
        print('Pulling Docker image: ' + image)
        _pull_image(image)

    tempdir = kwargs.get('_tempdir')
    args = _expand_args(task.get('container_args', []), inputs, task_inputs,
                        tempdir)

    ipipes, opipes = _setup_pipes(
        task_inputs, inputs, task_outputs, outputs, tempdir)

    pre_args = _get_pre_args(task, os.getuid(), os.getgid())
    command = [
        'docker', 'run',
        '-v', '%s:%s' % (tempdir, DATA_VOLUME),
        '-v', '%s:%s:ro' % (SCRIPTS_DIR, SCRIPTS_VOLUME),
        '--entrypoint', os.path.join(SCRIPTS_VOLUME, 'entrypoint.sh')
    ] + task.get('docker_run_args', []) + [image] + pre_args + args

    print('Running container: %s' % repr(command))

    p = utils.run_process(command, output_pipes=opipes, input_pipes=ipipes)

    if p.returncode != 0:
        raise Exception('Error: docker run returned code %d.' % p.returncode)

    print('Garbage collecting old containers and images.')
    gc_dir = os.path.join(tempdir, 'docker_gc_scratch')
    os.mkdir(gc_dir)
    p = _docker_gc(gc_dir)

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

    p.wait()  # Wait for garbage collection subprocess to finish

    if p.returncode != 0:
        raise Exception('Docker GC returned code %d.' % p.returncode)
