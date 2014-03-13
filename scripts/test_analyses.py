import cardoon
import json

fit_continuous = json.load(open("packaged/fit_continuous.json"))
print fit_continuous

output = cardoon.run(fit_continuous,
    inputs={
        "tree": {"format": "newick", "uri": "file://anolis.phy"},
        "table": {"format": "csv", "uri": "file://anolisDataAppended.csv"},
        "model": {"format": "text", "data": "OU"},
        "column": {"format": "text", "data": "SVL"}
    },
    outputs={
        "result": {"format": "nested"},
        "fit": {"format": "rows"}
    }
)

print output
