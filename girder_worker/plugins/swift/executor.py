import re
import tempfile

from girder_worker.core import utils


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

    pipes = {}
    for id in ('_stdout', '_stderr'):
        if id in task_outputs and id in outputs:
            pipes[id] = utils.AccumulateDictAdapter(outputs[id], 'script_data')

    command = ['swift', script_fname] + args

    print('Running swift: "%s"' % ' '.join(command))

    p = utils.run_process(command, output_pipes=pipes)

    if p.returncode != 0:
        raise Exception('Error: swift run returned code {}.'.format(
                        p.returncode))

    for name, task_output in task_outputs.iteritems():
        with open(name) as output_file:
            outputs[name]['script_data'] = output_file.read()
