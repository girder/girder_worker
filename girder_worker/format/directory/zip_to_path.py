import os
import zipfile


output = os.path.splitext(input)[0]

try:
    os.makedirs(output)
except OSError:
    if not os.path.exists(output):
        raise

with zipfile.ZipFile(input) as zf:
    zf.extractall(output)
