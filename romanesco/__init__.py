import imp
import json
import bson.json_util
import pymongo
import StringIO
import csv
import tempfile
import os
import urllib2
import romanesco.format
import romanesco.uri

def load(analysis_file):
    with open(analysis_file) as f:
        analysis = json.load(f)

    if not "script" in analysis:
        prevdir = os.getcwd()
        os.chdir(os.path.dirname(analysis_file))
        analysis["script"] = romanesco.uri.get_uri(analysis["script_uri"])
        os.chdir(prevdir)

    return analysis

def convert(type, input, output):
    if "data" not in input:
        input["data"] = romanesco.uri.get_uri(input["uri"])

    if input["format"] == output["format"]:
        data = input["data"]
    else:
        converter_path = romanesco.format.converters[type][input["format"]][output["format"]]
        data_descriptor = input
        for c in converter_path:
            result = romanesco.run(c, {"input": data_descriptor}, auto_convert=False)
            data_descriptor = result["output"]
        data = data_descriptor["data"]

    if "uri" in output:
        romanesco.uri.put_uri(data, output["uri"])
    else:
        output["data"] = data
    return output

def run(analysis, inputs, outputs=None, auto_convert=True):
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
        if auto_convert:
            converted = romanesco.convert(analysis_input["type"], d, {"format": analysis_input["format"]})
            d["script_data"] = converted["data"]
        elif d["format"] == analysis_input["format"]:
            if "data" not in d:
                d["data"] = romanesco.uri.get_uri(d["uri"])
            d["script_data"] = d["data"]
        else:
            raise Exception("Expected exact format match but '" + d["format"] + "' != '" + analysis_input["format"] + "'.")

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

        for name in inputs:
            rpy2.robjects.globalenv[str(name)] = inputs[name]["script_data"]

        rpy2.robjects.r(analysis["script"])

        for name, analysis_output in analysis_outputs.iteritems():
            d = outputs[name]
            d["script_data"] = rpy2.robjects.globalenv[str(name)]

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
        if auto_convert:
            outputs[name] = romanesco.convert(analysis_output["type"], {"data": d["script_data"], "format": analysis_output["format"]}, d)
        elif d["format"] == analysis_output["format"]:
            data = d["script_data"]
            if "uri" in d:
                romanesco.uri.put_uri(data, d["uri"])
            else:
                d["data"] = data
        else:
            raise Exception("Expected exact format match but '" + d["format"] + "' != '" + analysis_output["format"] + "'.")

        if "script_data" in outputs[name]:
            del outputs[name]["script_data"]

    return outputs
