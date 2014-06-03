output = []
for column in input["fields"]:
    if isinstance(data["rows"][0][column],str):
        output.append(column)