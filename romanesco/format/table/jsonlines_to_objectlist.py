import bson.json_util

output = [bson.json_util.loads(line) for line in input.splitlines()]
