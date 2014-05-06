import bson
import collections

output = {
    "fields": [],
    "rows": bson.decode_all(input, collections.OrderedDict)
}

if len(output["rows"]) > 0:
    output["fields"] = output["rows"][0].keys()
