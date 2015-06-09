import imp
import json
import sys
from romanesco import spark


def run(task, inputs, outputs, task_inputs, task_outputs, **kwargs):
    custom = imp.new_module("custom")

    # TODO
    # Ensure that the spark modules have been added to our path
    # Create SparkContext - Should we share one across a workflow?
    # Take any inputs and convert them to RDDS?
    print 'Running pyspark'

    sc = kwargs['_romanesco_spark_context']
    custom.__dict__['sc'] = sc
    custom.__dict__['spark_context'] = sc

    for name in inputs:
        custom.__dict__[name] = inputs[name]["script_data"]

    try:
        exec task["script"] in custom.__dict__
    except Exception, e:
        trace = sys.exc_info()[2]
        lines = task["script"].split("\n")
        lines = [(str(i+1) + ": " + lines[i]) for i in xrange(len(lines))]
        error = (
            str(e) + "\nScript:\n" + "\n".join(lines) +
            "\nTask:\n" + json.dumps(task, indent=4)
        )
        raise Exception(error), None, trace
    finally:
        sc.stop()

    for name, task_output in task_outputs.iteritems():
        outputs[name]["script_data"] = custom.__dict__[name]
