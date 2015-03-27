def fetch(spec, **kwargs):
    import pymongo
    import bson
    db = spec['db']
    collection = spec['collection']
    data = ''.join([bson.BSON.encode(d) for d in
                    pymongo.MongoClient(spec['host'])[db][collection].find()])
    return data


def push(spec, **kwargs):
    import pymongo
    import bson
    db = spec['db']
    collection = spec['collection']
    bson_data = bson.decode_all(data)
    # TODO is this really what we want? Dropping the whole collection?
    # Seems dangerous, might be unexpected.
    pymongo.MongoClient(spec['host'])[db][collection].drop()
    if len(bson_data) > 0:
        pymongo.MongoClient(spec['host'])[db][collection].insert(bson_data)
