import json
import StringIO
import tempfile
import os
import romanesco.format
import romanesco.uri

from . import tasks


# Maps task modes to their implementation
_taskMap = {
    'python': tasks.python.run,
    'r': tasks.r.run,
    'workflow': tasks.workflow.run
}


def load(analysis_file):
    """
    Load an analysis JSON into memory, resolving any ``"script_uri"`` fields
    by replacing it with a ``"script"`` field containing the contents pointed
    to by ``"script_uri"`` (see :py:mod:`romanesco.uri` for URI formats).

    :param analysis_file: The path to the JSON file to load.
    :returns: The analysis as a dictionary.
    """

    with open(analysis_file) as f:
        analysis = json.load(f)

    if "script" not in analysis and analysis.get("mode") != "workflow":
        prevdir = os.getcwd()
        parent = os.path.dirname(analysis_file)
        if parent != "":
            os.chdir(os.path.dirname(analysis_file))
        analysis["script"] = romanesco.uri.get_uri(analysis["script_uri"])
        os.chdir(prevdir)

    return analysis


def isvalid(type, binding):
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
        binding["data"] = romanesco.uri.get_uri(binding["uri"])
    validator = romanesco.format.validators[type][binding["format"]]
    outputs = romanesco.run(validator, {"input": binding}, auto_convert=False,
                            validate=False)
    return outputs["output"]["data"]


def convert(type, input, output):
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
        input["data"] = romanesco.uri.get_uri(input["uri"])

    if input["format"] == output["format"]:
        data = input["data"]
    else:
        converter_type = romanesco.format.converters[type]
        converter_path = converter_type[input["format"]][output["format"]]
        data_descriptor = input
        for c in converter_path:
            result = romanesco.run(c, {"input": data_descriptor},
                                   auto_convert=False)
            data_descriptor = result["output"]
        data = data_descriptor["data"]

    if "uri" in output:
        romanesco.uri.put_uri(data, output["uri"])
    else:
        output["data"] = data
    return output


def run(task, inputs, outputs=None, auto_convert=True, validate=True):
    """
    Run a Romanesco task with the specified I/O bindings.

    :param task: Specification of the task to run. The format of this
        specification is best described by the subclasses of
        :py:class:`romanesco.specs.TaskSpecification` class, which can be used
        to serialized this parameter.
    :type task: dict
    :param inputs: Specification of how input objects should be fetched
        into the runtime environment of this task. The format of this dict
        is best described by the
        :py:class:`romanesco.specs.InputBindingsSpecification` class, which can
        be used to serialize this parameter.
    :param outputs: Speficiation of what should be done with outputs
        of this task. The format of this dictionary is best defined in the
        :py:class:`romanesco.specs.OutputBindingsSpecification` class, which
        can be used to build and serialize this parameter.
    :type outputs: dict
    :param auto_convert: If ``True`` (the default), perform format conversions
        on inputs and outputs with :py:func:`convert` if they do not
        match the formats specified in the input and output bindings.
        If ``False``, an expection is raised for input or output bindings
        do not match the formats specified in the analysis.
    :param validate: If ``True``, perform input and output
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
    task_inputs = {d["name"]: d for d in task.get("input", ())}
    task_outputs = {d["name"]: d for d in task.get("output", ())}
    mode = task.get("mode") or "python"

    if mode not in _taskMap:
        raise Exception("Invalid mode: %s" % mode)

    for name, d in inputs.iteritems():
        task_input = task_inputs[name]

        # Validate the input
        if validate and not romanesco.isvalid(task_input["type"], d):
            raise Exception(
                "Input %s (Python type %s) is not in the expected type (%s) "
                "and format (%s)." % (
                    name, type(d["data"]), task_input["type"], d["format"])
                )

        # Convert data
        if auto_convert:
            converted = romanesco.convert(task_input["type"], d,
                                          {"format": task_input["format"]})
            d["script_data"] = converted["data"]
        elif d["format"] == task_input["format"]:
            if "data" not in d:  # TODO this will go away, replace with fetch
                d["data"] = romanesco.uri.get_uri(d["uri"])
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
    _taskMap[mode](task=task, inputs=inputs, outputs=outputs,
                   task_inputs=task_inputs, task_outputs=task_outputs)

    for name, task_output in task_outputs.iteritems():
        d = outputs[name]
        script_output = {"data": d["script_data"],
                         "format": task_output["format"]}

        # Validate the output
        if validate and not romanesco.isvalid(task_output["type"],
                                              script_output):
            raise Exception(
                "Output %s (%s) is not in the expected type (%s) and format "
                " (%s)." % (
                    name, type(script_output["data"]), task_output["type"],
                    d["format"])
                )

        if auto_convert:
            outputs[name] = romanesco.convert(
                task_output["type"], script_output, d)
        elif d["format"] == task_output["format"]:
            data = d["script_data"]
            if "uri" in d:  # TODO remove this
                romanesco.uri.put_uri(data, d["uri"])
            else:
                d["data"] = data
        else:
            raise Exception("Expected exact format match but %s != %s.'" % (
                d["format"], task_output["format"]))

        if "script_data" in outputs[name]:
            del outputs[name]["script_data"]

    return outputs
