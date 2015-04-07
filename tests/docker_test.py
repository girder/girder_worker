import httmock
import mock
import os
import romanesco
import shutil
import subprocess
import unittest

_tmp = None


def setUpModule():
    global _tmp
    _tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp')
    romanesco.config.set('romanesco', 'tmp_root', _tmp)


def tearDownModule():
    if os.path.isdir(_tmp):
        shutil.rmtree(_tmp)


class TestDockerMode(unittest.TestCase):
    @mock.patch('subprocess.Popen')
    def testDockerMode(self, mockPopen):
        processMock = mock.Mock()
        processMock.configure_mock(**{
            'communicate.return_value': ('ouput', 'error'),
            'returncode': 0
        })
        mockPopen.return_value = processMock

        task = {
            'mode': 'docker',
            'docker_image': 'test/test:latest',
            'container_args': ['-f', '$input{foo}'],
            'inputs': [{
                'id': 'foo',
                'name': 'A variable',
                'format': 'string',
                'type': 'string',
                'target': 'filepath'
            }]
        }

        inputs = {
            'foo': {
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
                task, inputs=inputs, cleanup=False, validate=False,
                auto_convert=False)

            self.assertEqual(out, {
                '_stderr': {
                    'script_data': 'error',
                    'format': 'string'
                },
                '_stdout': {
                    'script_data': 'ouput',
                    'format': 'string'
                }
            })

            self.assertEqual(mockPopen.call_count, 2)
            cmd1, cmd2 = [x[1]['args'] for x in mockPopen.call_args_list]

            self.assertEqual(cmd1, ('docker', 'pull', 'test/test:latest'))
            self.assertEqual(cmd2[:3], ['docker', 'run', '-v'])
            self.assertRegexpMatches(cmd2[3], _tmp + '/.*:/data')
            self.assertEqual(cmd2[4:],
                             ['test/test:latest', '-f', '/data/file.txt'])
