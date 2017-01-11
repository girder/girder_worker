import ConfigParser
import girder_worker
import httmock
import json
import mock
import os
import shutil
import six
import stat
import sys
import unittest

from girder_worker.core import run, io, TaskSpecValidationError
from girder_worker.plugins.docker.executor import DATA_VOLUME, SCRIPTS_VOLUME,\
    SCRIPTS_DIR

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

inspectOutput = json.dumps([{
    'Config': {
        'Entrypoint': ['/usr/bin/foo', '--flag']
    }
}], indent=4)


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
    @mock.patch('subprocess.check_output')
    @mock.patch('subprocess.Popen')
    def testDockerMode(self, mockPopen, checkOutput):
        mockPopen.return_value = processMock
        checkOutput.return_value = inspectOutput

        task = {
            'mode': 'docker',
            'docker_image': 'test/test:latest',
            'container_args': [
                '-f', '$input{foo}', '--temp-dir=$input{_tempdir}', '$flag{--bar}'],
            'pull_image': True,
            'inputs': [{
                'id': 'foo',
                'name': 'A variable',
                'format': 'string',
                'type': 'string',
                'target': 'filepath'
            }, {
                'id': '--bar',
                'name': 'bar',
                'format': 'boolean',
                'type': 'boolean'
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
            '--bar': {
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
            self.assertEqual(lines[0],
                             'Pulling Docker image: test/test:latest')
            self.assertEqual(lines[-2], 'output message')
            self.assertEqual(
                lines[-1], 'Garbage collecting old containers and images.')

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
            self.assertEqual(cmd2[:3],
                             ['docker', 'run', '-v'])
            six.assertRegex(self, cmd2[3], _tmp + '/.*:%s' % DATA_VOLUME)
            self.assertEqual(cmd2[4], '-v')
            six.assertRegex(self, cmd2[5],
                            '%s:%s:ro' % (SCRIPTS_DIR, SCRIPTS_VOLUME))
            self.assertEqual(cmd2[6:9], [
                '--entrypoint',
                '%s/entrypoint.sh' % SCRIPTS_VOLUME,
                'test/test:latest'
            ])
            self.assertEqual(cmd2[9:15], [
                str(os.getuid()), str(os.getgid()),
                '/usr/bin/foo', '--flag', '-f', '%s/file.txt' % DATA_VOLUME])
            self.assertEqual(cmd2[-2], '--temp-dir=%s' % DATA_VOLUME)
            self.assertEqual(cmd2[-1], '--bar')
            self.assertEqual(len(cmd2), 17)

            self.assertEqual(len(cmd3), 1)
            six.assertRegex(self, cmd3[0], 'docker-gc$')

            # Make sure we can specify a custom entrypoint to the container
            mockPopen.reset_mock()
            task['entrypoint'] = '/bin/bash'

            # Make sure additional docker run args work
            task['docker_run_args'] = ['--net', 'none']

            inputs['foo'] = {
                'mode': 'http',
                'url': 'https://foo.com/file.txt'
            }
            inputs['--bar'] = {
                'mode': 'inline',
                'data': False
            }
            run(task, inputs=inputs, validate=False, auto_convert=False)
            self.assertEqual(mockPopen.call_count, 3)
            cmd2 = mockPopen.call_args_list[1][1]['args']
            self.assertEqual(cmd2[6:11], [
                '--entrypoint',
                '%s/entrypoint.sh' % SCRIPTS_VOLUME,
                '--net',
                'none',
                'test/test:latest'
            ])
            self.assertNotIn('--bar', cmd2)
            self.assertEqual(cmd2[11:16], [
                str(os.getuid()), str(os.getgid()),
                '/bin/bash', '-f', '%s/file.txt' % DATA_VOLUME])

            mockPopen.reset_mock()
            # Make sure custom config settings are respected
            girder_worker.config.set('docker', 'cache_timeout', '123456')
            girder_worker.config.set(
                'docker', 'exclude_images', 'test/test:latest')

            # Make sure we can skip pulling the image
            task['pull_image'] = False
            inputs['foo'] = {
                'mode': 'http',
                'url': 'https://foo.com/file.txt'
            }
            out = run(task, inputs=inputs, validate=False,
                      auto_convert=False)
            self.assertEqual(mockPopen.call_count, 2)
            cmd1, cmd2 = [x[1]['args'] for x in mockPopen.call_args_list]
            self.assertEqual(tuple(cmd1[:2]), ('docker', 'run'))
            self.assertEqual(cmd1[8:10], ['--net', 'none'])
            six.assertRegex(self, cmd2[0], 'docker-gc$')
            env = mockPopen.call_args_list[1][1]['env']
            self.assertEqual(env['GRACE_PERIOD_SECONDS'], '123456')
            six.assertRegex(self, env['EXCLUDE_FROM_GC'],
                            'docker_gc_scratch/.docker-gc-exclude$')

    @mock.patch('subprocess.check_output')
    @mock.patch('subprocess.Popen')
    def testOutputValidation(self, mockPopen, checkOutput):
        mockPopen.return_value = processMock
        checkOutput.return_value = inspectOutput

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

        outputs = {
            'file_output_1': {
                'mode': 'http',
                'method': 'POST',
                'url': 'https://foo.com/file.txt'
            }
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
    @mock.patch('subprocess.check_output')
    def testNamedPipes(self, mockCheckOutput, mockPopen, mockRunProcess):
        mockRunProcess.return_value = processMock
        mockPopen.return_value = processMock
        mockCheckOutput.return_value = inspectOutput

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

        outputs = run(
            task, inputs={}, outputs=outputs, _tempdir=tmp, cleanup=False)

        # Make sure pipe was created inside the temp dir
        pipe = os.path.join(tmp, 'named_pipe')
        self.assertTrue(os.path.exists(pipe))
        self.assertTrue(stat.S_ISFIFO(os.stat(pipe).st_mode))
