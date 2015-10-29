import bson
import collections

opts = bson.codec_options.CodecOptions(
    collections.OrderedDict
)
output = bson.decode_all(input, opts)
