import events
import io
import json
import os

from executors.python import run as python_run
from executors.workflow import run as workflow_run
from . import utils

from girder_worker.utils import JobStatus, StateTransitionException
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


def set_job_status(mgr, status):
    if mgr:
        mgr.updateStatus(status)


def _extractId(spec):
    return spec['id'] if 'id' in spec else spec['name']


def _validateInputs(task_inputs, inputs):
    for name, task_input in task_inputs.iteritems():
        if name not in inputs:
            if 'default' in task_input:
                inputs[name] = task_input['default']
            else:
                raise Exception('Required input \'%s\' not provided.' % name)


@utils.with_tmpdir
def run(task, inputs=None, outputs=None, fetch=True, status=None, **kwargs):
    """
    Run a task with the specified I/O bindings.

    :param task: Specification of the task to run.
    :type task: dict
    :param inputs: Specification of how input objects should be fetched
        into the runtime environment of this task.
    :type inputs: dict
    :param outputs: Specification of what should be done with outputs
        of this task.
    :type outputs: dict
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
        ``{'data': data}``. The ``'data'`` field may be absent if an output URI
        was provided. Instead, those outputs will be saved to that URI and the
        output binding will contain the location in the ``'uri'`` field.
    """
    inputs = inputs or {}
    outputs = outputs or {}

    task_inputs = {_extractId(d): d for d in task.get('inputs', ())}
    task_outputs = {_extractId(d): d for d in task.get('outputs', ())}
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
        'status': status,
        'job_mgr': job_mgr,
        'kwargs': kwargs
    }
    events.trigger('run.before', info)

    try:
        # If some inputs are not there, fill in with defaults
        _validateInputs(task_inputs, inputs)

        for name, d in inputs.iteritems():
            task_input = task_inputs[name]
            if task_input.get('stream'):
                continue  # this input will be fetched as a stream

            if fetch:
                if status == JobStatus.RUNNING and 'data' not in d:
                    set_job_status(job_mgr, JobStatus.FETCHING_INPUT)
                d['data'] = io.fetch(d, **dict({'task_input': task_input}, **kwargs))

            events.trigger('run.handle_input', {
                'info': info,
                'task_input': task_input,
                'input': d,
                'name': name
            })

            if 'script_data' not in d:
                d['script_data'] = d['data']

        for name, task_output in task_outputs.iteritems():
            if name not in outputs:
                outputs[name] = {}

        # Set the appropriate job status flag
        set_job_status(job_mgr, status)

        # Actually run the task for the given mode
        _task_map[mode](
            task=task, inputs=inputs, outputs=outputs, task_inputs=task_inputs,
            task_outputs=task_outputs, **kwargs)

        for name, task_output in task_outputs.iteritems():
            if task_output.get('stream'):
                continue  # this output has already been sent as a stream

            output = outputs[name]
            e = events.trigger('run.handle_output', {
                'info': info,
                'task_output': task_output,
                'output': output,
                'outputs': outputs,
                'name': name
            })

            if not e.default_prevented:
                data = outputs[name]['script_data']

                if status == JobStatus.RUNNING:
                    set_job_status(job_mgr, JobStatus.PUSHING_OUTPUT)
                io.push(data, outputs[name], **dict({'task_output': task_output}, **kwargs))

            output.pop('script_data', None)

        events.trigger('run.after', info)

        return outputs
    except StateTransitionException:
        if job_mgr:
            status = job_mgr.refreshStatus()
            # If we are canceling we want to stay in that state, otherwise raise
            # the exception
            if status != JobStatus.CANCELING:
                raise
        else:
            raise
    finally:
        events.trigger('run.finally', info)


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
