import csv, StringIO
output = StringIO.StringIO()
if len(input) > 0:
    fields = [d for d in input[0]]
    writer = csv.DictWriter(output, fields)
    writer.writerow({d: d for d in fields})
    for d in input:
        writer.writerow(d)
output = output.getvalue()