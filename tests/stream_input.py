import sys

with open(sys.argv[1], 'r') as fd:
    for line in fd:
        print(line.strip()[::-1])
