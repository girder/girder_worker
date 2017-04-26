import imp
import json
import six
import sys


def run(task, inputs, outputs, task_inputs, task_outputs, **kwargs):
    from . import SC_KEY

    custom = imp.new_module('__girder_worker__')

    sc = kwargs[SC_KEY]
    custom.__dict__['sc'] = sc
    custom.__dict__['spark_context'] = sc
    custom.__dict__['_job_manager'] = kwargs.get('_job_manager')
    custom.__dict__['_tempdir'] = kwargs.get('_tempdir')

    for name in inputs:
        custom.__dict__[name] = inputs[name]['script_data']

    if task.get('write_script', kwargs.get('write_script', False)):
        import tempfile
        debug_path = tempfile.mktemp()
        with open(debug_path, 'wb') as fh:
            fh.write(task['script'])

        with open(debug_path, 'r') as fh:
            exec fh in custom.__dict__

    else:
        try:
            exec task['script'] in custom.__dict__
        except Exception, e:
            trace = sys.exc_info()[2]
            lines = task['script'].split('\n')
            lines = [(str(i+1) + ': ' + lines[i]) for i in xrange(len(lines))]
            error = (
                str(e) + '\nScript:\n' + '\n'.join(lines) +
                '\nTask:\n' + json.dumps(task, indent=4)
            )
            raise Exception(error), None, trace

    for name, task_output in six.viewitems(task_outputs):
        outputs[name]['script_data'] = custom.__dict__[name]
