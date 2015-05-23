import cStringIO
from romanesco.format import csv_to_rows

first_line = cStringIO.StringIO(input).readline()
output = csv_to_rows(first_line)['fields']
