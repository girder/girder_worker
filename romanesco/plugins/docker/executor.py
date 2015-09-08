import os
import re
import romanesco.utils
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

        newArgs.append(arg)

    return newArgs


def run(task, inputs, outputs, task_inputs, task_outputs, **kwargs):
    image = task['docker_image']
    print('Pulling docker image: ' + image)
    _pull_image(image)

    tmpDir = kwargs.get('_tmp_dir')
    args = _expand_args(task['container_args'], inputs, task_inputs, tmpDir)

    print_stderr, print_stdout = True, True
    for id, to in task_outputs.iteritems():
        if id == '_stderr':
            outputs['_stderr']['script_data'] = ''
            print_stderr = False
        elif id == '_stdout':
            outputs['_stdout']['script_data'] = ''
            print_stdout = False

    command = ['docker', 'run', '--rm', '-u', str(os.getuid())]

    if tmpDir:
        command += ['-v', tmpDir + ':/data']

    if 'entrypoint' in task:
        command += ['--entrypoint', task['entrypoint']]

    command += [image] + args

    print('Running container: "%s"' % ' '.join(command))

    p = romanesco.utils.run_process(command, outputs,
                                    print_stdout, print_stderr)

    if p.returncode != 0:
        raise Exception('Error: docker run returned code {}.'.format(
                        p.returncode))

    for name, task_output in task_outputs.iteritems():
        # TODO grab files written inside the container somehow?
        pass
