import bson

output = ''.join([bson.BSON.encode(row) for row in input])
