output = []
for column in input["fields"]:
    if isinstance(data["rows"][0][column],int) or isinstance(data["rows"][0][column],float):
        output.append(column)