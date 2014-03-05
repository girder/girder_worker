import cardoon
import json

fit_continuous = json.load(open("packaged/fit_continuous.json"))
print fit_continuous

cardoon.run(fit_continuous,
    inputs={
        "tree": {"format": "newick", "uri": "file://anolis.phy"},
        "table": {"format": "csv", "uri": "file://anolisDataAppended.csv"},
        "model": {"format": "python", "data": "OU"},
        "column": {"format": "python", "data": "SVL"}
    },
    outputs={
        "result": {"format": "newick", "uri": "file://anolis-fit-svl-ou.phy"},
        "fit": {"format": "csv", "uri": "file://anolis-fit-svl-ou.csv"}
    }
)
