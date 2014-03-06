import csv, StringIO
output = [d for d in csv.DictReader(input.splitlines())]

# Attempt numeric conversion
for row in output:
    for col in row:
        try:
            row[col] = int(row[col])
        except:
            try:
                row[col] = float(row[col])
            except:
                pass