import sys

if len(sys.argv) == 3:
    mode = sys.argv[1]
    message = sys.argv[2]

    if mode == 'stdio':
        print(message)
    elif mode == 'output_pipe':
        with open('/mnt/girder_worker/data/output_pipe', 'w') as fp:
            fp.write(message)
    elif mode == 'input_pipe':
        with open('/mnt/girder_worker/data/input_pipe', 'r') as fp:
            print(fp.read())
    elif mode == 'stdout_stderr':
        sys.stdout.write('this is stdout data\n')
        sys.stderr.write('this is stderr data\n')
    else:
        sys.stderr.write('Invalid test mode: "%s".\n' % mode)
        sys.exit(-1)
else:
    sys.stderr.write('Insufficient arguments.\n')
    sys.exit(-1)
