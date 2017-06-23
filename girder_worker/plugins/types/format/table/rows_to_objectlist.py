def set_nested(obj, path, v):
    key = path.pop()

    if len(path) == 0:
        obj[key] = v
        return

    obj[key] = {}
    set_nested(obj[key], path, v)


output = []
for row in input['rows']:
    item = {}
    for k, v in row.iteritems():
        path = k.split('.')
        path.reverse()
        set_nested(item, path, v)
    output.append(item)
