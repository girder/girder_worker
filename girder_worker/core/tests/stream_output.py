import sys

print('start')
with open(sys.argv[1], 'wb') as fd:
    fd.write(b'a message')
    fd.flush()
print('done')
