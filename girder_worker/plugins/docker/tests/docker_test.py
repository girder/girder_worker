import ConfigParser
import girder_worker
import httmock
import mock
import os
import shutil
import six
import stat
import sys
import unittest

from girder_worker.core import cleanup, run, io, TaskSpecValidationError
from girder_worker.plugins.docker.executor import DATA_VOLUME

_tmp = None
OUT_FD, ERR_FD = 100, 200
_out = six.StringIO('output message\n')
_err = six.StringIO('error message\n')

processMock = mock.Mock()
processMock.configure_mock(**{
    'communicate.return_value': ('', ''),
    'poll.return_value': 0,
    'stdout.fileno.return_value': OUT_FD,
    'stderr.fileno.return_value': ERR_FD,
    'returncode': 0
})


# Monkey patch select.select in the docker task module
def _mockSelect(r, w, x, *args, **kwargs):
    return r, w, x
girder_worker.core.utils.select.select = _mockSelect


# Monkey patch os.read to simulate subprocess stdout and stderr
def _mockOsRead(fd, *args, **kwargs):
    global _out, _err
    if fd == OUT_FD:
        return _out.read()
    elif fd == ERR_FD:
        return _err.read()
girder_worker.plugins.docker.executor.os.read = _mockOsRead


def setUpModule():
    global _tmp
    _tmp = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'tmp', 'docker')
    girder_worker.config.set('girder_worker', 'tmp_root', _tmp)
    try:
        girder_worker.config.add_section('docker')
    except ConfigParser.DuplicateSectionError:
        pass

    if os.path.isdir(_tmp):
        shutil.rmtree(_tmp)


def tearDownModule():
    if os.path.isdir(_tmp):
        shutil.rmtree(_tmp)


class TestDockerMode(unittest.TestCase):
    @mock.patch('subprocess.Popen')
    def testDockerMode(self, mockPopen):
        mockPopen.return_value = processMock

        task = {
            'mode': 'docker',
            'docker_image': 'test/test:latest',
            'container_args': [
                '-f', '$input{foo}', '--temp-dir=$input{_tempdir}',
                '$flag{bar}'
            ],
            'pull_image': True,
            'inputs': [{
                'id': 'foo',
                'name': 'A variable',
                'format': 'string',
                'type': 'string',
                'target': 'filepath'
            }, {
                'id': 'bar',
                'name': 'Bar',
                'format': 'boolean',
                'type': 'boolean',
                'arg': '--bar'
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
            },
            'bar': {
                'mode': 'inline',
                'data': True
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
            mockedStdOut = six.StringIO()
            sys.stdout = mockedStdOut
            out = run(
                task, inputs=inputs, cleanup=False, validate=False,
                auto_convert=False)
            sys.stdout = _old

            # We didn't specify _stdout as an output, so it should just get
            # printed to sys.stdout (which we mocked)
            lines = mockedStdOut.getvalue().splitlines()
            self.assertEqual(lines, ['output message'])

            # We bound _stderr as a task output, so it should be in the output
            self.assertEqual(out, {
                '_stderr': {
                    'data': 'error message\n',
                    'format': 'string'
                }
            })

            self.assertEqual(mockPopen.call_count, 3)
            cmd1, cmd2, cmd3 = [x[1]['args'] for x in mockPopen.call_args_list]

            self.assertEqual(cmd1, ('docker', 'pull', 'test/test:latest'))
            self.assertEqual(cmd2[:3], ['docker', 'run', '-v'])
            six.assertRegex(self, cmd2[3], _tmp + '/.*:%s' % DATA_VOLUME)
            self.assertEqual(cmd2[4:7], [
                'test/test:latest', '-f', '%s/file.txt' % DATA_VOLUME])
            self.assertEqual(cmd2[-2], '--temp-dir=%s' % DATA_VOLUME)
            self.assertEqual(cmd2[-1], '--bar')
            self.assertEqual(len(cmd2), 9)

            self.assertEqual(cmd3[:4], ['docker', 'run', '--rm', '-v'])
            six.assertRegex(self, cmd3[4], _tmp + '/.*:%s' % DATA_VOLUME)
            self.assertEqual(cmd3[5:], ['busybox', 'chmod', '-R', 'a+rw', DATA_VOLUME])
            self.assertEqual(len(cmd3), 10)

            # Make sure we can specify a custom entrypoint to the container
            mockPopen.reset_mock()
            task['entrypoint'] = '/bin/bash'

            # Make sure additional docker run args work
            task['docker_run_args'] = ['--net', 'none']

            inputs['foo'] = {
                'mode': 'http',
                'url': 'https://foo.com/file.txt'
            }
            inputs['bar'] = {
                'mode': 'inline',
                'data': False
            }
            run(task, inputs=inputs, validate=False, auto_convert=False)
            self.assertEqual(mockPopen.call_count, 3)
            cmd2 = mockPopen.call_args_list[1][1]['args']
            self.assertEqual(cmd2[4:9], [
                '--net', 'none', '--entrypoint', '/bin/bash', 'test/test:latest'])
            self.assertNotIn('--bar', cmd2)
            self.assertEqual(cmd2[9:11], ['-f', '%s/file.txt' % DATA_VOLUME])

            mockPopen.reset_mock()

            # Make sure we can skip pulling the image
            task['pull_image'] = False
            inputs['foo'] = {
                'mode': 'http',
                'url': 'https://foo.com/file.txt'
            }
            run(task, inputs=inputs, validate=False, auto_convert=False)
            self.assertEqual(mockPopen.call_count, 2)
            cmd1 = [x[1]['args'] for x in mockPopen.call_args_list][0]
            self.assertEqual(tuple(cmd1[:2]), ('docker', 'run'))
            self.assertEqual(cmd1[4:6], ['--net', 'none'])

    @mock.patch('subprocess.Popen')
    def testCleanupHook(self, mockPopen):
        os.makedirs(_tmp)
        mockPopen.return_value = processMock
        girder_worker.config.set('docker', 'cache_timeout', '123456')
        girder_worker.config.set('docker', 'exclude_images', 'test/test:latest')

        # Make sure docker-gc is called during cleanup
        cleanup.main()

        self.assertEqual(mockPopen.call_count, 1)
        cmd = [x[1]['args'] for x in mockPopen.call_args_list][0]

        six.assertRegex(self, cmd[0], 'docker-gc$')
        env = mockPopen.call_args_list[0][1]['env']
        self.assertEqual(env['GRACE_PERIOD_SECONDS'], '123456')
        six.assertRegex(self, env['EXCLUDE_FROM_GC'], r'\.docker-gc-exclude$')

    @mock.patch('subprocess.Popen')
    def testOutputValidation(self, mockPopen):
        mockPopen.return_value = processMock

        task = {
            'mode': 'docker',
            'docker_image': 'test/test',
            'pull_image': True,
            'inputs': [],
            'outputs': [{
                'id': 'file_output_1',
                'format': 'text',
                'type': 'string'
            }]
        }

        msg = (r'^Docker outputs must be either "_stdout", "_stderr", or '
               'filepath-target outputs\.$')
        with self.assertRaisesRegexp(TaskSpecValidationError, msg):
            run(task)

        task['outputs'][0]['target'] = 'filepath'
        task['outputs'][0]['path'] = '/tmp/some/invalid/path'
        msg = (r'^Docker filepath output paths must either start with "%s/" '
               'or be specified relative to that directory\.$' % DATA_VOLUME)
        with self.assertRaisesRegexp(TaskSpecValidationError, msg):
            run(task)

        task['outputs'][0]['path'] = '%s/valid_path.txt' % DATA_VOLUME
        path = os.path.join(_tmp, '.*', 'valid_path\.txt')
        msg = r'^Output filepath %s does not exist\.$' % path
        with self.assertRaisesRegexp(Exception, msg):
            run(task)
        # Make sure docker stuff actually got called in this case.
        self.assertEqual(mockPopen.call_count, 3)

        # Simulate a task that has written into the temp dir
        tmp = os.path.join(_tmp, 'simulated_output')
        if not os.path.isdir(tmp):
            os.makedirs(tmp)
        path = os.path.join(tmp, 'valid_path.txt')
        with open(path, 'w') as f:
            f.write('simulated output')
        outputs = run(task, _tempdir=tmp)
        self.assertEqual(outputs, {
            'file_output_1': {
                'data': path,
                'format': 'text'
            }
        })

        # If no path is specified, we should fall back to the input name
        del task['outputs'][0]['path']
        path = os.path.join(_tmp, '.*', 'file_output_1')
        msg = r'^Output filepath %s does not exist\.$' % path
        with self.assertRaisesRegexp(Exception, msg):
            run(task)

    @mock.patch('girder_worker.core.utils.run_process')
    @mock.patch('subprocess.Popen')
    def testNamedPipes(self, mockPopen, mockRunProcess):
        mockRunProcess.return_value = processMock
        mockPopen.return_value = processMock

        task = {
            'mode': 'docker',
            'docker_image': 'test/test',
            'pull_image': False,
            'inputs': [],
            'outputs': [{
                'id': 'named_pipe',
                'format': 'text',
                'type': 'string',
                'target': 'filepath',
                'stream': True
            }]
        }

        outputs = {
            'named_pipe': {
                'mode': 'test_dummy'
            }
        }

        class DummyAdapter(girder_worker.core.utils.StreamPushAdapter):
            def write(self, buf):
                pass

        # Mock out the stream adapter
        io.register_stream_push_adapter('test_dummy', DummyAdapter)

        tmp = os.path.join(_tmp, 'testing')
        if not os.path.isdir(tmp):
            os.makedirs(tmp)

        run(task, inputs={}, outputs=outputs, _tempdir=tmp, cleanup=False)

        # Make sure pipe was created inside the temp dir
        pipe = os.path.join(tmp, 'named_pipe')
        self.assertTrue(os.path.exists(pipe))
        self.assertTrue(stat.S_ISFIFO(os.stat(pipe).st_mode))
