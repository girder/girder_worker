import urllib2

def get_uri(uri):
    """
    Retrieve data from a URI.

    :param uri: The URI to retrieve in the form ``scheme://path``. The ``scheme`` may currently be
        anything supported by ``urllib2`` in addition to ``"mongodb"`` which uses the
        `standard connection string format`_ with a trailing ``"/collection-name"`` for the
        collection to retrieve.
        Web URIs are retrieved via a GET request.
        File paths may be relative to the current working directory by omitting a third slash and directly
        beginning the relative path.
    :returns: The data from the URI as a string.

    .. _`standard connection string format`: http://docs.mongodb.org/manual/reference/connection-string/#standard-connection-string-format
    """

    scheme = uri.split(":")[0]
    if scheme == "mongodb":
        import pymongo, bson
        parts = uri.split("/")
        db = parts[3]
        collection = parts[4]
        data = "".join([bson.BSON.encode(d) for d in pymongo.MongoClient(uri)[db][collection].find()])
    elif scheme == "file":
        return open(uri[7:]).read()
    else:
        data = urllib2.urlopen(uri).read()
    return data

def put_uri(data, uri):
    """
    Save data to a URI.

    :param data: The data, normally a byte string.
    :param uri: The URI to save the data to in the form ``scheme://path``.
        Web URIs are not currently supported, but ``"mongodb"`` and ``"file"`` schemes are
        supported identically to :py:func:`get_uri`. Existing files and MongoDB collections
        are replaced by the data.
    """

    scheme = uri.split(":")[0]
    if scheme == "mongodb":
        import pymongo, bson
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
