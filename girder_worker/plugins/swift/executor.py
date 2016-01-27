import re
import girder_worker.utils
import tempfile


def _expand_args(args, inputs, taskInputs, tmpDir):
    """
    Expands arguments to the container execution if they reference input
    data. For example, if an input has id=foo, then a container arg of the form
    $input{foo} would be expanded to the runtime value of that input.
    """
    newArgs = []
    regex = re.compile(r'\$input\{([^}]+)\}')

    for arg in args:
        for inputId in re.findall(regex, arg):
            if inputId in inputs:
                arg = arg.replace('$input{%s}' % inputId,
                                  inputs[inputId]['script_data'])
            elif inputId == '_tempdir':
                arg = arg.replace('$input{_tempdir}', tmpDir)

        newArgs.append(arg)

    return newArgs


def run(task, inputs, outputs, task_inputs, task_outputs, **kwargs):
    script = task['script']
    script_fname = tempfile.mktemp()
    with open(script_fname, 'w') as script_file:
        script_file.write(script)

    tmpDir = kwargs.get('_tempdir')
    args = _expand_args(task['swift_args'], inputs, task_inputs, tmpDir)

    print_stderr, print_stdout = True, True
    for id, to in task_outputs.iteritems():
        if id == '_stderr':
            outputs['_stderr']['script_data'] = ''
            print_stderr = False
        elif id == '_stdout':
            outputs['_stdout']['script_data'] = ''
            print_stdout = False

    command = ['swift', script_fname] + args

    print('Running swift: "%s"' % ' '.join(command))

    p = girder_worker.utils.run_process(command, outputs,
                                        print_stdout, print_stderr)

    if p.returncode != 0:
        raise Exception('Error: swift run returned code {}.'.format(
                        p.returncode))

    for name, task_output in task_outputs.iteritems():
        with open(name) as output_file:
            outputs[name]['script_data'] = output_file.read()
