import csv, StringIO
output = StringIO.StringIO()
writer = csv.DictWriter(output, input["fields"])
writer.writerow({d: d for d in input["fields"]})
for d in input["rows"]:
    writer.writerow(d)
output = output.getvalue()
