import os
import json

from girder_worker.core import utils


def _write_scala_script(script, inputs, task_outputs, tmp_dir):
    script_fname = os.path.join(tmp_dir, 'script.scala')
    with open(script_fname, 'w') as script_file:
        script_file.write('{\n')

        # Send input values to the script
        for name, binding in inputs.iteritems():
            value = json.dumps(binding['script_data'])
            script_file.write('val ' + name + ' = ' + value + '\n')

        # Run the script
        script_file.write(script)

        # Write output values to temporary files
        script_file.write('\nimport java.io._\n')
        for name in task_outputs:
            if name != '_stderr' and name != '_stdout':
                fname = os.path.join(tmp_dir, name)
                script_file.write("""
new PrintWriter({}) {{
    write({}); close
}}
""".format(json.dumps(fname), name + '.toString()'))

        # Exit the interactive shell
        script_file.write('}\n')
        script_file.write('System.exit(0)\n')

    return script_fname


def _run(spark, task, inputs, outputs, task_inputs, task_outputs, **kwargs):
    tmp_dir = kwargs.get('_tempdir')

    script_fname = _write_scala_script(
        task['script'], inputs, task_outputs, tmp_dir)

    pipes = {}
    for id in ('_stdout', '_stderr'):
        if id in task_outputs and id in outputs:
            pipes[id] = utils.AccumulateDictAdapter(outputs[id], 'script_data')

    if spark:
        command = ['spark-shell', '-i', script_fname]
    else:
        command = ['scala', script_fname]

    print('Running scala: "%s"' % ' '.join(command))

    p = utils.run_process(command, output_pipes=pipes)

    if p.returncode != 0:
        raise Exception('Error: scala run returned code {}.'.format(
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


def run(**kwargs):
    _run(spark=False, **kwargs)


def run_spark(**kwargs):
    _run(spark=True, **kwargs)
