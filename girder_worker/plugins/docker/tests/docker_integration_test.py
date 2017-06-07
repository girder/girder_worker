import ConfigParser
import os
import shutil
import six
import stat
import sys
import unittest
import docker
import mock
import threading
import time

import girder_worker
from girder_worker.core import run, io

TEST_IMAGE = 'girder/girder_worker_test:latest'


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
            'docker_image': TEST_IMAGE,
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
        celery_task = mock.MagicMock()
        celery_task.canceled = False

        _old = sys.stdout
        stdout_captor = six.StringIO()
        sys.stdout = stdout_captor
        run(
            task, inputs=inputs, _tempdir=self._tmp, cleanup=True, validate=False,
            auto_convert=False, _celery_task=celery_task)
        sys.stdout = _old
        lines = stdout_captor.getvalue().splitlines()
        self.assertEqual(lines[-1], self._test_message)

        task = {
            'mode': 'docker',
            'docker_image': TEST_IMAGE,
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
            auto_convert=False, _celery_task=celery_task)
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
            auto_convert=False, _celery_task=celery_task)
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
            'docker_image': TEST_IMAGE,
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

        celery_task = mock.MagicMock()
        celery_task.canceled = False

        outputs = run(
            task, inputs=inputs, outputs=outputs, _tempdir=self._tmp, cleanup=False,
            _celery_task=celery_task)

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
            'docker_image': TEST_IMAGE,
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

        celery_task = mock.MagicMock()
        celery_task.canceled = False

        output = run(
            task, inputs=inputs, outputs={}, _tempdir=self._tmp, cleanup=True,
            _celery_task=celery_task)

        # Make sure pipe was created inside the temp dir
        pipe = os.path.join(self._tmp, 'input_pipe')
        self.assertTrue(os.path.exists(pipe))
        self.assertTrue(stat.S_ISFIFO(os.stat(pipe).st_mode))
        self.assertEqual(output['_stdout']['data'].rstrip(), self._test_message)

    def testDockerModeRemoveContainer(self):
        """
        Test automatic container removal
        """
        container_name = 'testDockerModeRemoveContainer'
        task = {
            'mode': 'docker',
            'docker_image': TEST_IMAGE,
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
            'outputs': [],
            'docker_run_args': {
                'name': container_name
            }
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

        docker_client = docker.from_env()

        celery_task = mock.MagicMock()
        celery_task.canceled = False
        containers = []

        def _cleanup():
            for container in containers:
                container.remove()

        try:
            girder_worker.config.set('docker', 'gc', 'False')
            run(
                task, inputs=inputs, _tempdir=self._tmp, cleanup=True, validate=False,
                auto_convert=False, _celery_task=celery_task)

            containers = docker_client.containers.list(all=True, filters={
                'name': container_name
            })
            # Now assert that the container was removed
            self.assertEqual(len(containers), 0)
        finally:
            _cleanup()

        try:
            # Now confirm that the container doesn't get removed if we set
            # _rm_container = False
            girder_worker.config.set('docker', 'gc', 'True')
            # Stop GC removing anything
            girder_worker.config.set('docker', 'cache_timeout', str(sys.maxint))

            task['_rm_container'] = False
            run(
                task, inputs=inputs, _tempdir=self._tmp, cleanup=True, validate=False,
                auto_convert=False, _rm_containers=False, _celery_task=celery_task)
            containers = docker_client.containers.list(all=True, filters={
                'name': container_name
            })
            self.assertEqual(len(containers), 1)
        finally:
            _cleanup()

    def testDockerModeCancelKill(self):
        """
        Test container cancellation, requiring a sigkill
        """
        container_name = 'testDockerModeCancelKill'
        task = {
            'mode': 'docker',
            'docker_image': TEST_IMAGE,
            'pull_image': True,
            'container_args': ['$input{test_mode}', '$input{message}'],
            'inputs': [{
                'id': 'test_mode',
                'name': '',
                'format': 'string',
                'type': 'string'
            }],
            'outputs': [],
            '_rm_container': False,
            'docker_run_args': {
                'name': container_name
            }
        }

        inputs = {
            'test_mode': {
                'format': 'string',
                'data': 'sigkill'
            }
        }

        # We this set to True, so we can over the value for _rm_container
        girder_worker.config.set('docker', 'gc', 'True')
        # Stop GC removing anything
        girder_worker.config.set('docker', 'cache_timeout', str(sys.maxint))

        celery_task = mock.MagicMock()
        celery_task.canceled = False

        def _run():
            run(
                task, inputs=inputs, _tempdir=self._tmp, cleanup=True, validate=False,
                auto_convert=False, _celery_task=celery_task)

        run_thread = threading.Thread(target=_run)
        run_thread.start()

        docker_client = docker.from_env()

        # Wait for container to run
        tries = 15
        while tries > 0:
            containers = docker_client.containers.list(limit=1, filters={
                'name': container_name,
                'status': 'running'
            })

            if len(containers) > 0:
                break
            tries -= 1
            time.sleep(1)

        self.assertEqual(len(containers), 1)
        container = None
        try:
            container = containers[0]
            self.assertEqual(container.status, 'running')

            # Now switch canceled property and check that the container is stopped
            celery_task.canceled = True

            # Now wait for container to stop
            tries = 15
            while tries > 0:
                container.reload()
                if container.status == 'exited':
                    break
                tries -= 1
                time.sleep(1)

            self.assertEqual(container.status, 'exited')
        finally:
            if container is not None:
                container.remove()

    def testDockerModeCancelSigTerm(self):
        """
        Test container cancellation, using sigint
        """
        container_name = 'testDockerModeCancelSigTerm'
        task = {
            'mode': 'docker',
            'docker_image': TEST_IMAGE,
            'pull_image': True,
            'container_args': ['$input{test_mode}', '$input{message}'],
            'inputs': [{
                'id': 'test_mode',
                'name': '',
                'format': 'string',
                'type': 'string'
            }],
            'outputs': [],
            '_rm_container': False,
            'docker_run_args': {
                'name': container_name
            }
        }

        inputs = {
            'test_mode': {
                'format': 'string',
                'data': 'sigterm'
            }
        }

        # We this set to True, so we can over the value for _rm_container
        girder_worker.config.set('docker', 'gc', 'True')
        # Stop GC removing anything
        girder_worker.config.set('docker', 'cache_timeout', str(sys.maxint))

        celery_task = mock.MagicMock()
        celery_task.canceled = False

        container = None
        _old_stdout = None
        try:
            _old_stdout = sys.stdout
            stdout_captor = six.StringIO()
            sys.stdout = stdout_captor

            def _run():
                run(
                    task, inputs=inputs, _tempdir=self._tmp, cleanup=True, validate=False,
                    auto_convert=False, _celery_task=celery_task)

            run_thread = threading.Thread(target=_run)
            run_thread.start()

            docker_client = docker.from_env()

            # Wait for container to run
            tries = 15
            while tries > 0:
                containers = docker_client.containers.list(limit=1, filters={
                    'name': container_name,
                    'status': 'running'
                })

                if len(containers) > 0:
                    break
                tries -= 1
                time.sleep(1)

            self.assertEqual(len(containers), 1)

            container = containers[0]
            self.assertEqual(container.status, 'running')

            # Now switch canceled property and check that the container is stopped
            celery_task.canceled = True

            # Now wait for container to stop
            tries = 15
            while tries > 0:
                container.reload()
                if container.status == 'exited':
                    break
                tries -= 1
                time.sleep(1)

            self.assertEqual(container.status, 'exited')

        finally:
            if container is not None:
                container.remove()
            if _old_stdout is not None:
                sys.stdout = _old_stdout
            run_thread.join()


def testDockerModeStdErrStdOut(self):
        """
        Test writing to stdout and stderr.
        """

        task = {
            'mode': 'docker',
            'docker_image': TEST_IMAGE,
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
                'id': '_stdout',
                'format': 'string',
                'type': 'string'
            }, {
                'id': '_stderr',
                'format': 'string',
                'type': 'string'
            }]
        }

        inputs = {
            'test_mode': {
                'format': 'string',
                'data': 'stdout_stderr'
            },
            'message': {
                'format': 'string',
                'data': self._test_message
            }
        }

        out = run(
            task, inputs=inputs, _tempdir=self._tmp, cleanup=True, validate=False,
            auto_convert=False)

        self.assertEqual(out['_stdout']['data'], 'this is stdout data\n')
        self.assertEqual(out['_stderr']['data'], 'this is stderr data\n')
