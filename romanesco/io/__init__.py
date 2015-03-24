from __future__ import absolute_import

from . import http, mongodb


def fetch(spec, **kwargs):
    """
    This function can be called on any valid input binding specification and is
    responsible for performing any operations necessary to fetch the data. Once
    any fetch operations are complete, this returns the value to which the
    corresponding variable should be set.

    :param input_spec: The specification of the input to fetch. This is a
        LOCATION_SPEC type in the Romanesco grammar.
    :type input_spec: dict
    """
    if 'mode' not in spec:
        raise Exception('Missing input mode.')
    mode = spec['mode']

    if mode == 'http':
        return http.fetch(spec, **kwargs)
    elif mode == 'mongodb':
        return mongodb.fetch(spec, **kwargs)
    elif mode == 'inline':
        return spec['data']
    else:
        raise Exception('Unknown input fetch mode: ' + mode)


def put_uri(data, uri):
    """
    Save data to a URI.

    :param data: The data, normally a byte string.
    :param uri: The URI to save the data to in the form ``scheme://path``.
        Web URIs are not currently supported, but ``"mongodb"`` and ``"file"``
        schemes are supported identically to :py:func:`get_uri`. Existing files
        and MongoDB collections are replaced by the data.
    """

    scheme = uri.split(":")[0]
    if scheme == "mongodb":
        import pymongo
        import bson
        parts = uri.split("/")
        db = parts[3]
        collection = parts[4]
        bson_data = bson.decode_all(data)
        pymongo.MongoClient(uri)[db][collection].drop()
        if len(bson_data) > 0:
            pymongo.MongoClient(uri)[db][collection].insert(bson_data)
    elif scheme == "file":
        out_file = open(uri[7:], 'w')
        out_file.write(data)
        out_file.close()
    else:
        raise Exception("URI scheme not supported")
