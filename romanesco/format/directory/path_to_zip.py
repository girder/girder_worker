import os
import zipfile

output = input + '.zip'

with zipfile.ZipFile(output, 'w') as zf:
    for root, _, files in os.walk(input):
        for file in files:
            abspath = os.path.join(root, file)
            zf.write(os.path.join(root, file),
                     arcname=os.path.relpath(abspath, os.path.dirname(input)))
