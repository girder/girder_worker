import copy
import httmock
import os
import romanesco
import shutil
import unittest

_tmp = None


def setUpModule():
    global _tmp
    _tmp = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'tmp', 'fetch')
    romanesco.config.set('romanesco', 'tmp_root', _tmp)


def tearDownModule():
    if os.path.isdir(_tmp):
        shutil.rmtree(_tmp)


class TestFetch(unittest.TestCase):
    def testHttpFetch(self):
        task = {
            'mode': 'python',
            'script': 'y = x + "_suffix"',
            'inputs': [{
                'id': 'x',
                'name': 'x',
                'format': 'string',
                'type': 'string',
                'target': 'filepath',
                'filename': 'override.txt'
            }],
            'outputs': [{
                'id': 'y',
                'name': 'y',
                'format': 'string',
                'type': 'string'
            }]
        }

        inputs = {
            'x': {
                'mode': 'http',
                'url': 'https://foo.com/file.txt'
            }
        }

        @httmock.all_requests
        def fetchMock(url, request):
            if url.netloc == 'foo.com' and url.scheme == 'https':
                return 'dummy file contents'
            else:
                raise Exception('Unexpected url ' + repr(url))

        with httmock.HTTMock(fetchMock):
            # Use user-specified filename
            out = romanesco.run(
                task, inputs=copy.deepcopy(inputs),  cleanup=False,
                validate=False, auto_convert=False)

            val = out['y']['data']
            self.assertTrue(val.endswith('override.txt_suffix'))
            path = val[:-7]

            self.assertTrue(os.path.exists(path), path)
            with open(path) as f:
                contents = f.read()

            self.assertEqual(contents, 'dummy file contents')

            # Use automatically detected filename
            del task['inputs'][0]['filename']

            out = romanesco.run(
                task, inputs=copy.deepcopy(inputs), cleanup=False,
                validate=False, auto_convert=False)
            self.assertTrue(out['y']['data'].endswith('file.txt_suffix'))

            # Download to memory instead of a file (the default target value)
            del task['inputs'][0]['target']
            out = romanesco.run(
                task, inputs=copy.deepcopy(inputs), cleanup=False,
                validate=False, auto_convert=False)
            self.assertEqual(out['y']['data'], 'dummy file contents_suffix')
