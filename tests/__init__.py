import contextlib
import six
import sys


@contextlib.contextmanager
def captureOutput():
    oldout, olderr = sys.stdout, sys.stderr
    try:
        out = [six.BytesIO(), six.BytesIO()]
        sys.stdout, sys.stderr = out
        yield out
    finally:
        sys.stdout, sys.stderr = oldout, olderr
        out[0] = out[0].getvalue()
        out[1] = out[1].getvalue()
