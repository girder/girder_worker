import sys
import time
import signal

if len(sys.argv) == 3:
    mode = sys.argv[1]

    if mode == 'stdio':
        message = sys.argv[2]
        print(message)
    elif mode == 'output_pipe':
        message = sys.argv[2]
        with open('/mnt/girder_worker/data/output_pipe', 'w') as fp:
            fp.write(message)
    elif mode == 'input_pipe':
        with open('/mnt/girder_worker/data/input_pipe', 'r') as fp:
            print(fp.read())
    elif mode == 'sigkill':
        time.sleep(30)
    elif mode == 'sigterm':
        def _signal_handler(signal, frame):
            sys.exit(0)
        # Install signal handler
        signal.signal(signal.SIGTERM, _signal_handler)
        time.sleep(30)
    elif mode == 'stdout_stderr':
        sys.stdout.write('this is stdout data\n')
        sys.stderr.write('this is stderr data\n')
    elif mode == 'volume':
        path = sys.argv[2]
        with open(path) as fp:
            print(fp.read())
    else:
        sys.stderr.write('Invalid test mode: "%s".\n' % mode)
        sys.exit(-1)
else:
    sys.stderr.write('Insufficient arguments.\n')
    sys.exit(-1)
