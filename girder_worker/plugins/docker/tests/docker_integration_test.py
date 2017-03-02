import ConfigParser
import os
import shutil
import six
import stat
import sys
import unittest

import girder_worker
from girder_worker.core import run, io

test_image = 'girder/girder_worker_test:latest'


def setUpModule():
    global _tmp
    _tmp = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '_tmp', 'docker')
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
    """
    Integration tests that call out to docker rather than using mocks.
    """

    def setUp(self):
        self._test_message = 'Hello from girder_worker!'
        self._tmp = os.path.join(_tmp, 'testing')
        if not os.path.isdir(self._tmp):
            os.makedirs(self._tmp)

    def tearDown(self):
        shutil.rmtree(self._tmp)

    def testDockerModeStdio(self):
        """
        Test writing to stdout.
        """

        task = {
            'mode': 'docker',
            'docker_image': test_image,
            'pull_image': True,
            'container_args': ['$input{test_mode}', '$input{message}'],
            'inputs': [{
                'id': 'test_mode',
                'name': '',
                'format': 'string',
                'type': 'string'
            }, {
                'id': 'message',
                'name': '',
                'format': 'string',
                'type': 'string'
            }],
            'outputs': []
        }

        inputs = {
            'test_mode': {
                'format': 'string',
                'data': 'stdio'
            },
            'message': {
                'format': 'string',
                'data': self._test_message
            }
        }

        _old = sys.stdout
        stdout_captor = six.StringIO()
        sys.stdout = stdout_captor
        run(
            task, inputs=inputs, _tempdir=self._tmp, cleanup=True, validate=False,
            auto_convert=False)
        sys.stdout = _old
        lines = stdout_captor.getvalue().splitlines()
        self.assertEqual(lines[-1], self._test_message)

        task = {
            'mode': 'docker',
            'docker_image': test_image,
            'pull_image': True,
            'container_args': ['$input{test_mode}', '$input{message}'],
            'inputs': [{
                'id': 'test_mode',
                'name': '',
                'format': 'string',
                'type': 'string'
            }, {
                'id': 'message',
                'name': '',
                'format': 'string',
                'type': 'string'
            }],
            'outputs': []
        }
        _old = sys.stdout
        stdout_captor = six.StringIO()
        sys.stdout = stdout_captor
        run(
            task, inputs=inputs, cleanup=True, validate=False,
            auto_convert=False)
        sys.stdout = _old

        lines = stdout_captor.getvalue().splitlines()
        self.assertEqual(lines[-1], self._test_message)

        # Test _stdout
        task['outputs'] = [{
            'id': '_stdout',
            'format': 'string',
            'type': 'string'
        }]

        _old = sys.stdout
        stdout_captor = six.StringIO()
        sys.stdout = stdout_captor
        out = run(
            task, inputs=inputs, cleanup=False, validate=False,
            auto_convert=False)
        sys.stdout = _old

        lines = stdout_captor.getvalue().splitlines()
        message = '%s\n' % self._test_message
        self.assertTrue(message not in lines)
        self.assertEqual(out['_stdout']['data'], message)

    def testDockerModeOutputPipes(self):
        """
        Test writing to named output pipe.
        """
        task = {
            'mode': 'docker',
            'docker_image': test_image,
            'pull_image': True,
            'container_args': ['$input{test_mode}', '$input{message}'],
            'inputs': [{
                'id': 'test_mode',
                'name': '',
                'format': 'string',
                'type': 'string'
            }, {
                'id': 'message',
                'name': '',
                'format': 'string',
                'type': 'string'
            }],
            'outputs': [{
                'id': 'output_pipe',
                'format': 'text',
                'type': 'string',
                'target': 'filepath',
                'stream': True
            }]
        }

        outputs = {
            'output_pipe': {
                'mode': 'capture'
            }
        }

        inputs = {
            'test_mode': {
                'format': 'string',
                'data': 'output_pipe'
            },
            'message': {
                'format': 'string',
                'data': self._test_message,
            }
        }

        class CaptureAdapter(girder_worker.core.utils.StreamPushAdapter):
            message = ''

            def write(self, buf):
                CaptureAdapter.message += buf

        # Mock out the stream adapter
        io.register_stream_push_adapter('capture', CaptureAdapter)

        outputs = run(
            task, inputs=inputs, outputs=outputs, _tempdir=self._tmp, cleanup=False)

        # Make sure pipe was created inside the temp dir
        pipe = os.path.join(self._tmp, 'output_pipe')
        self.assertTrue(os.path.exists(pipe))
        self.assertTrue(stat.S_ISFIFO(os.stat(pipe).st_mode))
        # Make use piped output was write to adapter
        self.assertEqual(CaptureAdapter.message, self._test_message)

    def testDockerModeInputPipes(self):
        """
        Test reading from named output pipe.
        """

        task = {
            'mode': 'docker',
            'docker_image': test_image,
            'pull_image': True,
            'container_args': ['$input{test_mode}', '$input{message}'],
            'inputs': [{
                'id': 'test_mode',
                'name': '',
                'format': 'string',
                'type': 'string'
            }, {
                'id': 'message',
                'name': '',
                'format': 'string',
                'type': 'string'
            }, {
                'id': 'input_pipe',
                'format': 'string',
                'type': 'string',
                'target': 'filepath',
                'stream': True
            }],
            'outputs': [{
                'id': '_stdout',
                'format': 'string',
                'type': 'string'
            }]
        }

        inputs = {
            'test_mode': {
                'format': 'string',
                'data': 'input_pipe'
            },
            'message': {
                'format': 'string',
                'data': self._test_message
            },
            'input_pipe': {
                'mode': 'static',
                'data': self._test_message
            }
        }

        # Mock out the stream adapter
        class StaticAdapter(girder_worker.core.utils.StreamFetchAdapter):

            def __init__(self, spec):
                self._data = six.BytesIO(spec['data'])

            def read(self, buf_len):
                return self._data.read(buf_len)

        io.register_stream_fetch_adapter('static', StaticAdapter)

        output = run(
            task, inputs=inputs, outputs={}, _tempdir=self._tmp, cleanup=True)

        # Make sure pipe was created inside the temp dir
        pipe = os.path.join(self._tmp, 'input_pipe')
        self.assertTrue(os.path.exists(pipe))
        self.assertTrue(stat.S_ISFIFO(os.stat(pipe).st_mode))
        self.assertEqual(output['_stdout']['data'].rstrip(), self._test_message)
