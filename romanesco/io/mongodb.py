def fetch(spec, **kwargs):
    import pymongo
    import bson
    db = spec['db']
    collection = spec['collection']
    host = spec.get('host', 'localhost')
    data = ''.join([bson.BSON.encode(d) for d in
                    pymongo.MongoClient(host)[db][collection].find()])
    return data


def push(data, spec, **kwargs):
    import pymongo
    import bson
    db = spec['db']
    collection = spec['collection']
    host = spec.get('host', 'localhost')
    bson_data = bson.decode_all(data)

    c = pymongo.MongoClient(host)[db][collection]
    # TODO is this really what we want? Dropping the whole collection?
    # Seems dangerous, might be unexpected.
    c.drop()
    if len(bson_data) > 0:
        c.insert(bson_data)
