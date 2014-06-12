import bson
import collections

output = bson.decode_all(input, collections.OrderedDict)
