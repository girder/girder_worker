import bson
output = "".join([bson.BSON.encode(d) for d in input])