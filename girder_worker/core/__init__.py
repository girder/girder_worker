import events
import io
import json
import os

from format import (
    converter_path, get_validator_analysis, Validator)

from executors.python import run as python_run
from executors.workflow import run as workflow_run
from networkx import NetworkXNoPath
from . import utils

from girder_worker import config, PACKAGE_DIR

# Maps task modes to their implementation
_task_map = {}


class TaskSpecValidationError(Exception):
    pass


def register_executor(name, fn):
    """
    Register a new executor in the girder_worker runtime. This is used to
    map the 'mode' field of a task to a function that will execute the task.

    :param name: The value of the mode field that maps to the given function.
    :type name: str
    :param fn: The implementing function.
    :type fn: function
    """
    _task_map[name] = fn


def unregister_executor(name):
    """
    Unregister an executor from the map.

    :param name: The name of the executor to unregister.
    :type name: str
    """
    del _task_map[name]

register_executor('python', python_run)
register_executor('workflow', workflow_run)

# Load plugins that are enabled in the config file or env var
_plugins = os.environ.get('WORKER_PLUGINS_ENABLED',
                          config.get('girder_worker', 'plugins_enabled'))
_plugins = [p.strip() for p in _plugins.split(',') if p.strip()]
_paths = os.environ.get(
    'WORKER_PLUGIN_LOAD_PATH', config.get(
        'girder_worker', 'plugin_load_path')).split(':')
_paths = [p for p in _paths if p.strip()]
_paths.append(os.path.join(PACKAGE_DIR, 'plugins'))
utils.load_plugins(_plugins, _paths, quiet=True)


def _resolve_scripts(task):
    if task.get('mode') != 'workflow':
        if 'script_uri' in task and 'script' not in task:
            task['script'] = io.fetch({
                'url': task['script_uri']
            })
    elif 'steps' in task:
        for step in task['steps']:
            _resolve_scripts(step['task'])


def load(task_file):
    """
    Load a task JSON into memory, resolving any ``'script_uri'`` fields
    by replacing it with a ``'script'`` field containing the contents pointed
    to by ``'script_uri'`` (see :py:mod:`girder_worker.uri` for URI formats). A
    ``script_fetch_mode`` field may also be set

    :param task_file: The path to the JSON file to load.
    :returns: The task as a dictionary.
    """

    with open(task_file) as f:
        task = json.load(f)

    prevdir = os.getcwd()
    parent = os.path.dirname(task_file)
    if parent != '':
        os.chdir(os.path.dirname(task_file))
    _resolve_scripts(task)
    os.chdir(prevdir)

    return task


def isvalid(type, binding, fetch=True, **kwargs):
    """
    Determine whether a data binding is of the appropriate type and format.

    :param type: The expected type specifier string of the binding.
    :param binding: A binding dict of the form
        ``{'format': format, 'data', data}``, where ``format`` is the format
        specifier string, and ``data`` is the raw data to test.
        The dict may also be of the form
        ``{'format': format, 'uri', uri}``, where ``uri`` is the location of
        the data (see :py:mod:`girder_worker.uri` for URI formats).
    :param fetch: Whether to do an initial data fetch before conversion
        (default ``True``).
    :returns: ``True`` if the binding matches the type and format,
        ``False`` otherwise.
    """
    analysis = get_validator_analysis(Validator(type, binding['format']))
    outputs = run(analysis, {'input': binding},
                  auto_convert=False,
                  validate=False, fetch=fetch, **kwargs)
    return outputs['output']['data']


def convert(type, input, output, fetch=True, status=None, **kwargs):
    """
    Convert data from one format to another.

    :param type: The type specifier string of the input data.
    :param input: A binding dict of the form
        ``{'format': format, 'data', data}``, where ``format`` is the format
        specifier string, and ``data`` is the raw data to convert.
        The dict may also be of the form
        ``{'format': format, 'uri', uri}``, where ``uri`` is the location of
        the data (see :py:mod:`girder_worker.uri` for URI formats).
    :param output: A binding of the form
        ``{'format': format}``, where ``format`` is the format
        specifier string to convert the data to.
        The binding may also be in the form
        ``{'format': format, 'uri', uri}``, where ``uri`` specifies
        where to place the converted data.
    :param fetch: Whether to do an initial data fetch before conversion
        (default ``True``).
    :returns: The output binding
        dict with an additional field ``'data'`` containing the converted data.
        If ``'uri'`` is present in the output binding, instead saves the data
        to the specified URI and
        returns the output binding unchanged.
    """
    if fetch:
        input['data'] = io.fetch(input, **kwargs)

    if input['format'] == output['format']:
        data = input['data']
    else:
        data_descriptor = input
        try:
            conversion_path = converter_path(Validator(type, input['format']),
                                             Validator(type, output['format']))
        except NetworkXNoPath:
            raise Exception('No conversion path from %s/%s to %s/%s' %
                            (type, input['format'], type, output['format']))

        # Run data_descriptor through each conversion in the path
        for conversion in conversion_path:
            result = run(conversion, {'input': data_descriptor},
                         auto_convert=False, status=status,
                         **kwargs)
            data_descriptor = result['output']
        data = data_descriptor['data']

    if status == utils.JobStatus.CONVERTING_OUTPUT:
        job_mgr = kwargs.get('_job_manager')
        _job_status(job_mgr, utils.JobStatus.PUSHING_OUTPUT)
    io.push(data, output, **kwargs)
    return output


def _job_status(mgr, status):
    if mgr:
        mgr.updateStatus(status)


@utils.with_tmpdir  # noqa
def run(task, inputs=None, outputs=None, auto_convert=True, validate=True,
        fetch=True, status=None, **kwargs):
    """
    Run a task with the specified I/O bindings.

    :param task: Specification of the task to run.
    :type task: dict
    :param inputs: Specification of how input objects should be fetched
        into the runtime environment of this task.
    :type inputs: dict
    :param outputs: Speficiation of what should be done with outputs
        of this task.
    :type outputs: dict
    :param auto_convert: If ``True`` (the default), perform format conversions
        on inputs and outputs with :py:func:`convert` if they do not
        match the formats specified in the input and output bindings.
        If ``False``, an expection is raised for input or output bindings
        do not match the formats specified in the analysis.
    :param validate: If ``True`` (the default), perform input and output
        validation with :py:func:`isvalid` to ensure input bindings are in the
        appropriate format and outputs generated by the script are
        formatted correctly. This guards against dirty input as well as
        buggy scripts that do not produce the correct type of output. An
        invalid input or output will raise an exception. If ``False``, perform
        no validation.
    :param write_script: If ``True`` task scripts will be written to file before
        being passed to ``exec``. This improves interactive debugging with
        tools such as ``pdb`` at the cost of additional file I/O. Note that
        when passed to run *all* tasks will be written to file including
        validation and conversion tasks.
    :param fetch: If ``True`` will perform a fetch on the input before
        running the task (default ``True``).
    :param status: Job status to update to during execution of this task.
    :type status: girder_worker.utils.JobStatus
    :returns: A dictionary of the form ``name: binding`` where ``name`` is
        the name of the output and ``binding`` is an output binding of the form
        ``{'format': format, 'data': data}``. If the `outputs` param
        is specified, the formats of these bindings will match those given in
        `outputs`. Additionally, ``'data'`` may be absent if an output URI
        was provided. Instead, those outputs will be saved to that URI and
        the output binding will contain the location in the ``'uri'`` field.
    """
    def extractId(spec):
        return spec['id'] if 'id' in spec else spec['name']

    if inputs is None:
        inputs = {}

    task_inputs = {extractId(d): d for d in task.get('inputs', ())}
    task_outputs = {extractId(d): d for d in task.get('outputs', ())}
    mode = task.get('mode', 'python')

    if mode not in _task_map:
        raise Exception('Invalid mode: %s' % mode)

    job_mgr = kwargs.get('_job_manager')

    info = {
        'task': task,
        'task_inputs': task_inputs,
        'task_outputs': task_outputs,
        'mode': mode,
        'inputs': inputs,
        'outputs': outputs,
        'auto_convert': auto_convert,
        'validate': validate,
        'kwargs': kwargs
    }
    events.trigger('run.before', info)

    try:
        # If some inputs are not there, fill in with defaults
        for name, task_input in task_inputs.iteritems():
            if name not in inputs:
                if 'default' in task_input:
                    inputs[name] = task_input['default']
                else:
                    raise Exception(
                        'Required input \'%s\' not provided.' % name)

        for name, d in inputs.iteritems():
            task_input = task_inputs[name]
            if task_input.get('stream'):
                continue  # this input will be fetched as a stream

            # Fetch the input
            if fetch:
                if status == utils.JobStatus.RUNNING and 'data' not in d:
                    _job_status(job_mgr, utils.JobStatus.FETCHING_INPUT)
                d['data'] = io.fetch(
                    d, **dict({'task_input': task_input}, **kwargs))

            # Validate the input
            if validate and not isvalid(
                    task_input['type'], d,
                    **dict(
                        {'task_input': task_input, 'fetch': False}, **kwargs)):
                raise Exception(
                    'Input %s (Python type %s) is not in the expected type '
                    '(%s) and format (%s).' % (
                        name, type(d['data']), task_input['type'], d['format'])
                    )

            # Convert data
            if auto_convert:
                try:
                    converted = convert(
                        task_input['type'], d, {'format': task_input['format']},
                        status=utils.JobStatus.CONVERTING_INPUT,
                        **dict(
                            {'task_input': task_input, 'fetch': False},
                            **kwargs))
                except Exception, e:
                    raise Exception('%s: %s' % (name, str(e)))

                d['script_data'] = converted['data']
            elif (d.get('format', task_input.get('format')) ==
                  task_input.get('format')):
                d['script_data'] = d['data']
            else:
                raise Exception(
                    'Expected exact format match but \'%s != %s\'.' % (
                        d['format'], task_input['format'])
                )

        # Make sure all outputs are there
        if outputs is None:
            outputs = {}

        for name, task_output in task_outputs.iteritems():
            if name not in outputs:
                outputs[name] = {'format': task_output['format']}

        # Set the appropriate job status flag
        _job_status(job_mgr, status)

        # Actually run the task for the given mode
        _task_map[mode](task=task, inputs=inputs, outputs=outputs,
                        task_inputs=task_inputs, task_outputs=task_outputs,
                        auto_convert=auto_convert, validate=validate, **kwargs)

        for name, task_output in task_outputs.iteritems():
            if task_output.get('stream'):
                continue  # this output has already been sent as a stream

            d = outputs[name]
            script_output = {'data': d['script_data'],
                             'format': task_output['format']}

            # Validate the output
            if validate and not isvalid(
                    task_output['type'], script_output,
                    **dict({'task_output': task_output}, **kwargs)):
                raise Exception(
                    'Output %s (%s) is not in the expected type (%s) and '
                    'format (%s).' % (
                        name, type(script_output['data']), task_output['type'],
                        d['format'])
                    )

            # We should consider refactoring the logic below, reasoning about
            # the paths through this code is difficult, since this logic is
            # entered by 'run', 'isvalid', and 'convert'.
            if auto_convert:
                outputs[name] = convert(
                    task_output['type'], script_output, d,
                    status=utils.JobStatus.CONVERTING_OUTPUT,
                    **dict({'task_output': task_output}, **kwargs))
            elif d['format'] == task_output['format']:
                data = d['script_data']

                if status == utils.JobStatus.RUNNING:
                    _job_status(job_mgr, utils.JobStatus.PUSHING_OUTPUT)
                io.push(
                    data, d, **dict({'task_output': task_output}, **kwargs))
            else:
                raise Exception('Expected exact format match but %s != %s.' % (
                    d['format'], task_output['format']))

            if 'script_data' in outputs[name]:
                del outputs[name]['script_data']

        events.trigger('run.after', info)

        return outputs
    finally:
        events.trigger('run.finally', info)
