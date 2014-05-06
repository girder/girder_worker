import csv
import StringIO

output = StringIO.StringIO()
writer = csv.DictWriter(output, input["fields"], delimiter='\t')
writer.writerow({d: d for d in input["fields"]})
for d in input["rows"]:
    writer.writerow(d)
output = output.getvalue()
