import os
import tarfile

output = input + '.tgz'

with tarfile.open(output, 'w:gz') as tf:
    tf.add(input, arcname=os.path.basename(input))
