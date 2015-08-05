import httmock
import mock
import os
import romanesco
import select
import shutil
import StringIO
import sys
import unittest

_tmp = None
OUT_FD, ERR_FD = 100, 200
_out = StringIO.StringIO('output message')
_err = StringIO.StringIO('error message')


# Monkey patch select.select in the docker task module
def _mockSelect(r, w, x, *args, **kwargs):
    return r, w, x
romanesco.plugins.docker.executor.select.select = _mockSelect


# Monkey patch os.read to simulate subprocess stdout and stderr
def _mockOsRead(fd, *args, **kwargs):
    global _out, _err
    if fd == OUT_FD:
        return _out.read()
    elif fd == ERR_FD:
        return _err.read()
romanesco.plugins.docker.executor.os.read = _mockOsRead


def setUpModule():
    global _tmp
    _tmp = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'tmp', 'docker')
    romanesco.config.set('romanesco', 'tmp_root', _tmp)


def tearDownModule():
    if os.path.isdir(_tmp):
        shutil.rmtree(_tmp)


class TestDockerMode(unittest.TestCase):
    @mock.patch('subprocess.Popen')
    def testDockerMode(self, mockPopen):
        processMock = mock.Mock()
        processMock.configure_mock(**{
            'communicate.return_value': ('', ''),
            'poll.return_value': 0,
            'stdout.fileno.return_value': OUT_FD,
            'stderr.fileno.return_value': ERR_FD,
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
            }],
            'outputs': [{
                'id': '_stderr',
                'format': 'string',
                'type': 'string'
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
            _old = sys.stdout
            mockedStdOut = StringIO.StringIO()
            sys.stdout = mockedStdOut
            out = romanesco.run(
                task, inputs=inputs, cleanup=False, validate=False,
                auto_convert=False)
            sys.stdout = _old

            # We didn't specify _stdout as an output, so it should just get
            # printed to sys.stdout (which we mocked)
            lines = mockedStdOut.getvalue().splitlines()
            self.assertEqual(lines[0],
                             'Pulling docker image: test/test:latest')
            self.assertEqual(lines[-1], 'output message')

            # We bound _stderr as a task output, so it should be in the output
            self.assertEqual(out, {
                '_stderr': {
                    'data': 'error message',
                    'format': 'string'
                }
            })

            self.assertEqual(mockPopen.call_count, 2)
            cmd1, cmd2 = [x[1]['args'] for x in mockPopen.call_args_list]

            self.assertEqual(cmd1, ('docker', 'pull', 'test/test:latest'))
            self.assertEqual(cmd2[:6],
                             ['docker', 'run', '--rm', '-u',
                              str(os.getuid()), '-v'])
            self.assertRegexpMatches(cmd2[6], _tmp + '/.*:/data')
            self.assertEqual(cmd2[7:],
                             ['test/test:latest', '-f', '/data/file.txt'])

            # Make sure we can specify a custom entrypoint to the container
            mockPopen.reset_mock()
            task['entrypoint'] = '/bin/bash'
            out = romanesco.run(task, inputs=inputs, validate=False,
                                auto_convert=False)
            self.assertEqual(mockPopen.call_count, 2)
            cmd2 = mockPopen.call_args_list[1][1]['args']
            self.assertEqual(cmd2[:6],
                             ['docker', 'run', '--rm', '-u',
                              str(os.getuid()), '-v'])
            self.assertRegexpMatches(cmd2[6], _tmp + '/.*:/data')
            self.assertEqual(cmd2[7:9], ['--entrypoint', '/bin/bash'])
