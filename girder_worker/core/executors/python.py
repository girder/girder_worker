import imp
import json
import six
import tempfile


def run(task, inputs, outputs, task_inputs, task_outputs, **kwargs):
    custom = imp.new_module('__girder_worker__')

    custom.__dict__['_job_manager'] = kwargs.get('_job_manager')
    custom.__dict__['_tempdir'] = kwargs.get('_tempdir')

    for name in inputs:
        custom.__dict__[name] = inputs[name]['script_data']

    if task.get('write_script', kwargs.get('write_script', False)):
        debug_path = tempfile.mktemp()
        with open(debug_path, 'wb') as fh:
            fh.write(task['script'])

        with open(debug_path, 'r') as fh:
            exec(fh.read(), custom.__dict__)

    else:
        try:
            exec(task['script'], custom.__dict__)
        except Exception as e:
            lines = task['script'].split('\n')
            lines = ['%d: %s' % (i, line) for i, line in enumerate(lines, 1)]
            error = (
                str(e) + '\nScript:\n' + '\n'.join(lines) +
                '\nTask:\n' + json.dumps(task, indent=4)
            )
            six.raise_from(Exception(error), e)

    for name, task_output in task_outputs.iteritems():
        outputs[name]['script_data'] = custom.__dict__[name]
