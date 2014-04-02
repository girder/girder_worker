import urllib2

def get_uri(uri):
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
