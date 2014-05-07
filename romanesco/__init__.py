import imp
import json
import StringIO
import csv
import tempfile
import os
import urllib2
import romanesco.format
import romanesco.uri


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

    if "script" not in analysis:
        prevdir = os.getcwd()
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


def run(analysis, inputs, outputs=None, auto_convert=True, validate=True):
    """
    Run a Romanesco analysis with the specified input bindings and returns
    the outputs.

    :param analysis: A dictionary specifying the analysis to run. An analysis
        consists of the fields:

        :inputs: A list of input dicts of the form
            ``{"name": name, "type": type, "format": format}``
            where ``name`` is the variable name used in the script,
            ``type`` is the type specifier string for the input,
            and ``format`` is the format specifier string for the input.
        :outputs: A list of output specifier dicts of the form
            ``{"name": name, "type": type, "format": format}``
            where ``name`` is the variable name used in the script,
            ``type`` is the type specifier string for the output,
            and ``format`` is the format specifier string for the output.
        :mode: The mode of the analysis, currently ``"r"`` or ``"python"``.
        :script: The script to execute. The script should assume variables
            with names matching the inputs are already set with the provided
            types and formats. After performing the desired computation,
            the analysis should set
            variables with names matching the outputs, ensuring these are
            in the provided output types and formats.
    :param inputs: A dictionary specifying input bindings.
        It should be of the form ``name: binding`` where ``name``
        is the name of the input and ``binding`` is a data binding of the form
        ``{"format": format, "data", data}``. ``format`` is the format
        specifier string, and ``data`` is the raw data.
        The binding may also be of the form
        ``{"format": format, "uri", uri}``, where ``uri`` is the location of
        the data (see :py:mod:`romanesco.uri` for URI formats).
    :param outputs: An optional dictionary specifying output formats and
        locations. It should be of the form ``name: binding``
        where ``name``
        is the name of the output and ``binding`` is a data binding of the form
        ``{"format": format}``.
        The binding may also be of the form
        ``{"format": format, "uri", uri}``, where ``uri`` is the location where
        to put the data. If this argument is omitted, output bindings matching
        the analysis format speficiers are returned with inline ``"data"``
        fields.
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
        ``{"format": format, "data": data}``. If the `outputs` parameter
        is specified, the formats of these bindings will match those given in
        `outputs`. Additionally, ``"data"`` may be absent if an output URI
        was provided. Instead, those outputs will be saved to that URI and
        the output binding will contain the location in the ``"uri"`` field.
    """

    analysis_inputs = {d["name"]: d for d in analysis["inputs"]}
    analysis_outputs = {d["name"]: d for d in analysis["outputs"]}

    mode = analysis["mode"] if "mode" in analysis else "python"

    # If some inputs are not there, fill in with defaults
    for name, analysis_input in analysis_inputs.iteritems():
        if name not in inputs:
            if "default" in analysis_input:
                inputs[name] = analysis_input["default"]
            else:
                raise Exception("Required input '" + name + "' not provided.")

    for name in inputs:
        d = inputs[name]
        analysis_input = analysis_inputs[name]

        # Validate the input
        if validate and not romanesco.isvalid(analysis_input["type"], d):
            raise Exception("Input " + name + " (Python type "
                            + str(type(d["data"]))
                            + ") is not in the expected type ("
                            + analysis_input["type"]
                            + ") and format (" + d["format"] + ").")

        if auto_convert:
            converted = romanesco.convert(analysis_input["type"], d,
                                          {"format": analysis_input["format"]})
            d["script_data"] = converted["data"]
        elif d["format"] == analysis_input["format"]:
            if "data" not in d:
                d["data"] = romanesco.uri.get_uri(d["uri"])
            d["script_data"] = d["data"]
        else:
            raise Exception("Expected exact format match but '" + d["format"]
                            + "' != '" + analysis_input["format"] + "'.")

    # Make sure all outputs are there
    outputs = {} if outputs is None else outputs
    for name, analysis_output in analysis_outputs.iteritems():
        if name not in outputs:
            outputs[name] = {"format": analysis_output["format"]}

    if mode == "python":
        custom = imp.new_module("custom")

        for name in inputs:
            custom.__dict__[name] = inputs[name]["script_data"]

        exec analysis["script"] in custom.__dict__

        for name, analysis_output in analysis_outputs.iteritems():
            d = outputs[name]
            d["script_data"] = custom.__dict__[name]

    elif mode == "r":
        import rpy2.robjects

        env = rpy2.robjects.globalenv

        # Clear out workspace variables and packages
        rpy2.robjects.reval("""
            rm(list = ls())
            pkgs <- names(sessionInfo()$otherPkgs)
            if (!is.null(pkgs)) {
                pkgs <- paste('package:', pkgs, sep = "")
                lapply(pkgs, detach, character.only = TRUE, unload = TRUE)
            }
            """, env)

        for name in inputs:
            env[str(name)] = inputs[name]["script_data"]

        rpy2.robjects.reval(analysis["script"], env)

        for name, analysis_output in analysis_outputs.iteritems():
            d = outputs[name]
            d["script_data"] = env[str(name)]

            # Hack to detect scalar values from R.
            # The R value might not have a len() so wrap in a try/except.
            try:
                if len(d["script_data"]) == 1:
                    d["script_data"] = d["script_data"][0]
            except TypeError:
                pass
    else:
        raise Exception("Unsupported analysis mode")

    for name, analysis_output in analysis_outputs.iteritems():
        d = outputs[name]
        script_output = {"data": d["script_data"],
                         "format": analysis_output["format"]}

        # Validate the output
        if validate and not romanesco.isvalid(analysis_output["type"],
                                              script_output):
            raise Exception("Output " + name + " ("
                            + str(type(script_output["data"]))
                            + ") is not in the expected type ("
                            + analysis_output["type"] + ") and format ("
                            + d["format"] + ").")

        if auto_convert:
            outputs[name] = romanesco.convert(analysis_output["type"],
                                              script_output, d)
        elif d["format"] == analysis_output["format"]:
            data = d["script_data"]
            if "uri" in d:
                romanesco.uri.put_uri(data, d["uri"])
            else:
                d["data"] = data
        else:
            raise Exception("Expected exact format match but '" + d["format"]
                            + "' != '" + analysis_output["format"] + "'.")

        if "script_data" in outputs[name]:
            del outputs[name]["script_data"]

    return outputs
