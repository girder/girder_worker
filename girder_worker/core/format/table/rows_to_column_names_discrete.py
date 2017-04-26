import six

output = []
for column in input['fields']:
    if isinstance(input['rows'][0][column], (six.binary_type, six.text_type)):
        output.append(column)
