output = []
for column in input['fields']:
    if isinstance(input['rows'][0][column], (str, unicode)):
        output.append(column)
