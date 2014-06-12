import collections

# Attempt to keep column ordering if objects happen to have ordered keys
field_map = collections.OrderedDict()
for obj in input:
    for key in obj:
        if (isinstance(key, (str, unicode))):
            field_map[key] = True

fields = [key for key in field_map]

output = {"fields": fields, "rows": input}
