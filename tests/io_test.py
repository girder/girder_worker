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


class TestIo(unittest.TestCase):
    def testDefaultInline(self):
        task = {
            'mode': 'python',
            'script': 'b = a ** 2',
            'inputs': [{
                'id': 'a',
                'format': 'number',
                'type': 'number'
            }],
            'outputs': [{
                'id': 'b',
                'format': 'number',
                'type': 'number'
            }]
        }

        # Mode should default to "inline" if data key is set
        inputs = {
            'a': {
                'data': 5,
                'format': 'number',
                'type': 'number'
            }
        }

        outputs = romanesco.run(task, inputs)
        self.assertEqual(outputs['b']['data'], 25)

    def testHttpIo(self):
        task = {
            'mode': 'python',
            'script': 'y = x + "_suffix"\nfoo="bar"',
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
            }, {
                'id': 'foo',
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

        outputs = {
            'foo': {
                'mode': 'http',
                'format': 'string',
                'url': 'https://output.com/location.out',
                'headers': {'foo': 'bar'},
                'method': 'PUT'
            }
        }

        received = []

        @httmock.all_requests
        def fetchMock(url, request):
            if url.netloc == 'foo.com' and url.scheme == 'https':
                # The input fetch request
                return 'dummy file contents'
            elif url.netloc == 'output.com' and url.path == '/location.out':
                received.append(request.body)
                return ''
            else:
                raise Exception('Unexpected url ' + repr(url))

        with httmock.HTTMock(fetchMock):
            # Use user-specified filename
            out = romanesco.run(
                task, inputs=copy.deepcopy(inputs), outputs=outputs,
                cleanup=False, validate=False, auto_convert=False)

            val = out['y']['data']
            self.assertTrue(val.endswith('override.txt_suffix'))
            path = val[:-7]

            self.assertTrue(os.path.exists(path), path)
            with open(path) as f:
                contents = f.read()

            self.assertEqual(contents, 'dummy file contents')

            # Make sure our output endpoint was pushed to exactly once
            self.assertEqual(len(received), 1)
            self.assertEqual(received[0], 'bar')

            # Make sure the bound output didn't get returned
            self.assertFalse('data' in out['foo'])

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
