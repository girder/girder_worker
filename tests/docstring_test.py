import sys
import importlib
import doctest

from base import TestCase  # noqa


if __name__ == '__main__':

    error = 0
    total = 0
    fail = 0
    for module in sys.argv[1:]:
        if module == '-v':
            continue
        try:
            mod = importlib.import_module(module)
        except ImportError:
            error += 1
            print('Could not import {0}.'.format(module))
            continue
        result = doctest.testmod(mod)
        fail += result[0]
        total += result[1]

    if error:
        print('{0} modules failed to import'.format(error))
    print('{0} tests failed out of {1}'.format(fail, total))
    if error or fail:
        sys.exit(1)
