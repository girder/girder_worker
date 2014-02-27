import csv, StringIO
output = [d for d in csv.DictReader(StringIO.StringIO(input))]