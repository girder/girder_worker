output = []
for column in input['fields']:
    if isinstance(input['rows'][0][column], (int, float)):
        output.append(column)
