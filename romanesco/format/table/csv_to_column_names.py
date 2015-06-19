from six import StringIO
from romanesco.format import csv_to_rows

first_line = StringIO(input).readline()
output = csv_to_rows(first_line)['fields']
