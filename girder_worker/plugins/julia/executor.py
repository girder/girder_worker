import os
import json

from girder_worker.core import utils


def _write_julia_script(script, inputs, task_outputs, tmp_dir):
    script_fname = os.path.join(tmp_dir, 'script.julia')
    with open(script_fname, 'w') as script_file:
        # Send input values to the script
        for name, binding in inputs.iteritems():
            value = json.dumps(binding['script_data'])
            script_file.write(name + ' = ' + value + '\n')

        # Run the script
        script_file.write(script)

        # Write output values to temporary files
        for name in task_outputs:
            if name != '_stderr' and name != '_stdout':
                fname = os.path.join(tmp_dir, name)
                script_file.write("""
outfile = open({}, "w")
write(outfile, "${}")
close(outfile)
""".format(json.dumps(fname), name))

    return script_fname


def run(task, inputs, outputs, task_inputs, task_outputs, **kwargs):
    tmp_dir = kwargs.get('_tempdir')

    script_fname = _write_julia_script(
        task['script'], inputs, task_outputs, tmp_dir)

    pipes = {}
    for id in ('_stdout', '_stderr'):
        if id in task_outputs and id in outputs:
            pipes[id] = utils.AccumulateDictAdapter(outputs[id], 'script_data')

    command = ['julia', script_fname]

    print('Running julia: "%s"' % ' '.join(command))

    p = utils.run_process(command, output_pipes=pipes)

    if p.returncode != 0:
        raise Exception('Error: julia run returned code {}.'.format(
                        p.returncode))

    for name, task_output in task_outputs.iteritems():
        if name != '_stderr' and name != '_stdout':
            fname = os.path.join(tmp_dir, name)
            with open(fname) as output_file:
                outputs[name]['script_data'] = output_file.read()

            # Deal with converting from string - assume JSON
            if task_output['type'] in ('number', 'boolean'):
                outputs[name]['script_data'] = json.loads(
                    outputs[name]['script_data'])
