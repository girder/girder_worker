import csv
reader = csv.DictReader(input.splitlines())
output = {"fields": reader.fieldnames, "rows": [d for d in reader]}

# Attempt numeric conversion
for row in output["rows"]:
    for col in row:
        try:
            row[col] = int(row[col])
        except:
            try:
                row[col] = float(row[col])
            except:
                pass