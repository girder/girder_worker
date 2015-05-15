from netCDF4 import Dataset
import tempfile
import os

tmp = tempfile.mktemp()
with open(tmp, 'wb') as tmpfile:
    tmpfile.write(input)
output = Dataset(tmp, diskless=True)
os.remove(tmp)
