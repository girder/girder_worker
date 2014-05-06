import bson
import collections

output = "".join([bson.BSON.encode(collections.OrderedDict((key, row[key])
                  for key in input["fields"])) for row in input["rows"]])
