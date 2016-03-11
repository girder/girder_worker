import os
import re
import girder_worker.utils
import subprocess


def _pull_image(image):
    """
    Pulls the specified docker image onto this worker.
    """
    command = ('docker', 'pull', image)
    p = subprocess.Popen(args=command, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()

    if p.returncode != 0:
        print('Error pulling docker image %s:' % image)
        print('STDOUT: ' + stdout)
        print('STDERR: ' + stderr)

        raise Exception('Docker pull returned code {}.'.format(p.returncode))


def _transform_path(inputs, taskInputs, inputId, tmpDir):
    """
    If the input specified by inputId is a filepath target, we transform it to
    its absolute path within the docker container (underneath /data).
    """
    for ti in taskInputs.itervalues():
        tiId = ti['id'] if 'id' in ti else ti['name']
        if tiId == inputId:
            if ti.get('target') == 'filepath':
                rel = os.path.relpath(inputs[inputId]['script_data'], tmpDir)
                return os.path.join('/data', rel)
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
                arg = arg.replace('$input{_tempdir}', '/data')

        newArgs.append(arg)

    return newArgs


def _docker_gc():
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
    """
    script = os.path.join(os.path.dirname(__file__), 'docker-gc')
    if not os.path.isfile(script):
        raise Exception('Docker GC script %s not found.' % script)
    if not os.access(script, os.X_OK):
        raise Exception('Docker GC script %s is not executable.' % script)

    env = os.environ.copy()
    env['FORCE_CONTAINER_REMOVAL'] = '1'
    return subprocess.Popen(args=(script,), env=env)


def run(task, inputs, outputs, task_inputs, task_outputs, **kwargs):
    image = task['docker_image']
    print('Pulling docker image: ' + image)
    _pull_image(image)

    tmpDir = kwargs.get('_tempdir')
    args = _expand_args(task['container_args'], inputs, task_inputs, tmpDir)

    print_stderr, print_stdout = True, True
    for id, to in task_outputs.iteritems():
        if id == '_stderr':
            outputs['_stderr']['script_data'] = ''
            print_stderr = False
        elif id == '_stdout':
            outputs['_stdout']['script_data'] = ''
            print_stdout = False

    command = ['docker', 'run', '-u', str(os.getuid())]

    if tmpDir:
        command += ['-v', tmpDir + ':/data']

    if 'entrypoint' in task:
        command += ['--entrypoint', task['entrypoint']]

    command += [image] + args

    print('Running container: "%s"' % ' '.join(command))

    p = girder_worker.utils.run_process(command, outputs,
                                        print_stdout, print_stderr)

    if p.returncode != 0:
        raise Exception('Error: docker run returned code %d.' % p.returncode)

    print('Garbage collecting old containers and images.')
    p = _docker_gc()

    for name, task_output in task_outputs.iteritems():
        # TODO grab files written inside the container somehow?
        pass

    p.wait()  # Wait for garbage collection subprocess to finish

    if p.returncode != 0:
        raise Exception('Docker GC returned code %d.' % p.returncode)
