import json
import tempfile
import os
import romanesco.events
import romanesco.format
import romanesco.io
from romanesco.format import converter_path, get_validator

from ConfigParser import ConfigParser
from . import executors, utils


PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))

# Read the configuration files
_cfgs = ('worker.dist.cfg', 'worker.local.cfg')
config = ConfigParser()
config.read([os.path.join(PACKAGE_DIR, f) for f in _cfgs])

# Maps task modes to their implementation
_task_map = {}


def register_executor(name, fn):
    """
    Register a new executor in the romanesco runtime. This is used to map the
    "mode" field of a task to a function that will execute the task.

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


# Register the core executors that are always enabled.
register_executor('python', executors.python.run)
register_executor('workflow', executors.workflow.run)

# Load plugins that are enabled in the config file
_plugins = os.environ.get('ROMANESCO_PLUGINS_ENABLED',
                          config.get('romanesco', 'plugins_enabled'))
_plugins = [p.strip() for p in _plugins.split(',') if p.strip()]
_paths = os.environ.get('ROMANESCO_PLUGIN_LOAD_PATH',
                        config.get('romanesco', 'plugin_load_path')).split(':')
_paths = [p for p in _paths if p.strip()]
_paths.append(os.path.join(PACKAGE_DIR, 'plugins'))
utils.load_plugins(_plugins, _paths)


def load(task_file):
    """
    Load a task JSON into memory, resolving any ``"script_uri"`` fields
    by replacing it with a ``"script"`` field containing the contents pointed
    to by ``"script_uri"`` (see :py:mod:`romanesco.uri` for URI formats). A
    ``script_fetch_mode`` field may also be set

    :param analysis_file: The path to the JSON file to load.
    :returns: The analysis as a dictionary.
    """

    with open(task_file) as f:
        task = json.load(f)

    if "script" not in task and task.get("mode") != "workflow":
        prevdir = os.getcwd()
        parent = os.path.dirname(task_file)
        if parent != "":
            os.chdir(os.path.dirname(task_file))
        task["script"] = romanesco.io.fetch({
            "url": task["script_uri"]
        })
        os.chdir(prevdir)

    return task


def isvalid(type, binding, **kwargs):
    """
    Determine whether a data binding is of the appropriate type and format.

    :param type: The expected type specifier string of the binding.
    :param binding: A binding dict of the form
        ``{"format": format, "data", data}``, where ``format`` is the format
        specifier string, and ``data`` is the raw data to test.
        The dict may also be of the form
        ``{"format": format, "uri", uri}``, where ``uri`` is the location of
        the data (see :py:mod:`romanesco.uri` for URI formats).
    :returns: ``True`` if the binding matches the type and format,
        ``False`` otherwise.
    """
    if "data" not in binding:
        binding["data"] = romanesco.io.fetch(binding, **kwargs)
    validator = get_validator(type, binding["format"])[1]
    outputs = romanesco.run(validator, {"input": binding}, auto_convert=False,
                            validate=False, **kwargs)
    return outputs["output"]["data"]


def convert(type, input, output, **kwargs):
    """
    Convert data from one format to another.

    :param type: The type specifier string of the input data.
    :param input: A binding dict of the form
        ``{"format": format, "data", data}``, where ``format`` is the format
        specifier string, and ``data`` is the raw data to convert.
        The dict may also be of the form
        ``{"format": format, "uri", uri}``, where ``uri`` is the location of
        the data (see :py:mod:`romanesco.uri` for URI formats).
    :param output: A binding of the form
        ``{"format": format}``, where ``format`` is the format
        specifier string to convert the data to.
        The binding may also be in the form
        ``{"format": format, "uri", uri}``, where ``uri`` specifies
        where to place the converted data.
    :returns: The output binding
        dict with an additional field ``"data"`` containing the converted data.
        If ``"uri"`` is present in the output binding, instead saves the data
        to the specified URI and
        returns the output binding unchanged.
    """

    if "data" not in input:
        input["data"] = romanesco.io.fetch(input, **kwargs)

    if input["format"] == output["format"]:
        data = input["data"]
    else:
        data_descriptor = input
        for c in converter_path((type, input['format']),
                                (type, output['format'])):
            result = romanesco.run(c, {"input": data_descriptor},
                                   auto_convert=False, **kwargs)
            data_descriptor = result["output"]
        data = data_descriptor["data"]

    if "mode" in output:
        romanesco.io.push(data, output)
    else:
        output["data"] = data
    return output


@utils.with_tmpdir
def run(task, inputs, outputs=None, auto_convert=True, validate=True,
        **kwargs):
    """
    Run a Romanesco task with the specified I/O bindings.

    :param task: Specification of the task to run.
    :type task: dict
    :param inputs: Specification of how input objects should be fetched
        into the runtime environment of this task.
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
    :returns: A dictionary of the form ``name: binding`` where ``name`` is
        the name of the output and ``binding`` is an output binding of the form
        ``{"format": format, "data": data}``. If the `outputs` param
        is specified, the formats of these bindings will match those given in
        `outputs`. Additionally, ``"data"`` may be absent if an output URI
        was provided. Instead, those outputs will be saved to that URI and
        the output binding will contain the location in the ``"uri"`` field.
    """
    def extractId(spec):
        return spec["id"] if "id" in spec else spec["name"]

    if 'validator' in task:
        task = task['validator']

    task_inputs = {extractId(d): d for d in task.get("inputs", ())}
    task_outputs = {extractId(d): d for d in task.get("outputs", ())}
    mode = task.get("mode", "python")

    if mode not in _task_map:
        raise Exception("Invalid mode: %s" % mode)

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
    romanesco.events.trigger('run.before', info)

    try:
        # If some inputs are not there, fill in with defaults
        for name, task_input in task_inputs.iteritems():
            if name not in inputs:
                if "default" in task_input:
                    inputs[name] = task_input["default"]
                else:
                    raise Exception("Required input '%s' not provided." % name)

        for name, d in inputs.iteritems():
            task_input = task_inputs[name]

            # Validate the input
            if validate and not romanesco.isvalid(task_input["type"], d, **kwargs):
                raise Exception(
                    "Input %s (Python type %s) is not in the expected type (%s) "
                    "and format (%s)." % (
                        name, type(d["data"]), task_input["type"], d["format"])
                    )

            # Convert data
            if auto_convert:
                converted = romanesco.convert(task_input["type"], d,
                                              {"format": task_input["format"]}, **kwargs)
                d["script_data"] = converted["data"]
            elif (d.get("format", task_input.get("format")) ==
                  task_input.get("format")):
                if "data" not in d:
                    d["data"] = romanesco.io.fetch(
                        d, task_input=task_input, **kwargs)
                d["script_data"] = d["data"]
            else:
                raise Exception("Expected exact format match but '%s != %s'." % (
                    d["format"], task_input["format"])
                )

        # Make sure all outputs are there
        if outputs is None:
            outputs = {}

        for name, task_output in task_outputs.iteritems():
            if name not in outputs:
                outputs[name] = {"format": task_output["format"]}

        # Actually run the task for the given mode
        _task_map[mode](task=task, inputs=inputs, outputs=outputs,
                        task_inputs=task_inputs, task_outputs=task_outputs,
                        auto_convert=auto_convert, validate=validate, **kwargs)

        for name, task_output in task_outputs.iteritems():
            d = outputs[name]
            script_output = {"data": d["script_data"],
                             "format": task_output["format"]}

            # Validate the output
            if validate and not romanesco.isvalid(task_output["type"],
                                                  script_output, **kwargs):
                raise Exception(
                    "Output %s (%s) is not in the expected type (%s) and format "
                    " (%s)." % (
                        name, type(script_output["data"]), task_output["type"],
                        d["format"])
                    )

            if auto_convert:
                outputs[name] = romanesco.convert(
                    task_output["type"], script_output, d, **kwargs)
            elif d["format"] == task_output["format"]:
                data = d["script_data"]
                if d.get("mode"):
                    romanesco.io.push(data, d, task_output=task_output, **kwargs)
                else:
                    d["data"] = data
            else:
                raise Exception("Expected exact format match but %s != %s.'" % (
                    d["format"], task_output["format"]))

            if "script_data" in outputs[name]:
                del outputs[name]["script_data"]

        romanesco.events.trigger('run.after', info)

        return outputs
    finally:
        romanesco.events.trigger('run.finally', info)
