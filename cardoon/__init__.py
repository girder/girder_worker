import imp
import json
import bson.json_util
import pymongo
import StringIO
import csv
import tempfile
import os
import urllib2
import cardoon.format
import cardoon.uri

def load(analysis_file):
    with open(analysis_file) as f:
        analysis = json.load(f)

    if not "script" in analysis:
        prevdir = os.getcwd()
        os.chdir(os.path.dirname(analysis_file))
        analysis["script"] = cardoon.uri.get_uri(analysis["script_uri"])
        os.chdir(prevdir)

    return analysis

def run(analysis, inputs, outputs=None, auto_convert=True):
    analysis_inputs = {d["name"]: d for d in analysis["inputs"]}
    analysis_outputs = {d["name"]: d for d in analysis["outputs"]}

    mode = analysis["mode"] if "mode" in analysis else "python"

    for name in inputs:
        d = inputs[name]
        if "data" not in d:
            d["data"] = cardoon.uri.get_uri(d["uri"])
        analysis_input = analysis_inputs[name]
        if auto_convert:
            d["script_data"] = cardoon.format.convert(d["data"], analysis_input["type"], d["format"], analysis_input["format"])
        elif d["format"] == analysis_input["format"]:
            d["script_data"] = d["data"]
        else:
            raise Exception("Expected exact format match but '" + d["format"] + "' != '" + analysis_input["format"] + "'.")

    # Make sure all outputs are there
    outputs = {} if outputs is None else outputs
    for name, analysis_output in analysis_outputs.iteritems():
        if name not in outputs:
            outputs[name] = analysis_output

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

            # Hack to detect scalar values from R
            if len(d["script_data"]) == 1:
                d["script_data"] = d["script_data"][0]
    else:
        raise Exception("Unsupported analysis mode")

    for name, analysis_output in analysis_outputs.iteritems():
        d = outputs[name]
        if auto_convert:
            data = cardoon.format.convert(d["script_data"], analysis_output["type"], analysis_output["format"], d["format"])
        elif d["format"] == analysis_output["format"]:
            data = d["script_data"]
        else:
            raise Exception("Expected exact format match but '" + d["format"] + "' != '" + analysis_output["format"] + "'.")

        del d["script_data"]

        if "uri" in d:
            cardoon.uri.put_uri(data, d["uri"])
        else:
            d["data"] = data

    return outputs
