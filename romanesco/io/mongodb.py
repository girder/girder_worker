def fetch(spec, **kwargs):
    import pymongo
    import bson
    db = spec['db']
    collection = spec['collection']
    data = ''.join([bson.BSON.encode(d) for d in
                    pymongo.MongoClient(uri)[db][collection].find()])
    return data
