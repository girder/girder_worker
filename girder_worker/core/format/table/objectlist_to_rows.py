import collections
import six

# Attempt to keep column ordering if objects happen to have ordered keys
field_map = collections.OrderedDict()
rows = []


def subkeys(path, obj, row):
    if isinstance(obj, dict):
        for k in obj:
            if isinstance(k, (six.binary_type, six.text_type)):
                subkeys(path + [k], obj[k], row)
    elif len(path) > 0:
        field = '.'.join(path)
        field_map[field] = True
        row[field] = obj

for obj in input:
    row = {}
    subkeys([], obj, row)
    rows.append(row)

fields = [key for key in field_map]

output = {'fields': fields, 'rows': rows}
