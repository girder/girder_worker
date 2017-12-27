import copy
import httmock
import os
import shutil
import unittest

import girder_worker
from girder_worker.utils import JobStatus

import girder_worker.core


_tmp = None


def setUpModule():
    global _tmp
    _tmp = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'tmp', 'fetch')
    girder_worker.config.set('girder_worker', 'tmp_root', _tmp)


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

        outputs = girder_worker.core.run(task, inputs)
        self.assertEqual(outputs['b']['data'], 25)

    def testInlineFilepath(self):
        task = {
            'mode': 'python',
            'script': """
fname = file
with open(file) as f:
    out = f.read()
""",
            'inputs': [{
                'id': 'file',
                'format': 'text',
                'type': 'string',
                'target': 'filepath'
            }],
            'outputs': [
                {
                    'id': 'out',
                    'format': 'text',
                    'type': 'string'
                },
                {
                    'id': 'fname',
                    'format': 'text',
                    'type': 'string'
                }
            ]
        }

        # Test filepath input
        inputs = {
            'file': {
                'data': 'a,b,c\n1,2,3\n',
                'format': 'text',
                'type': 'string'
            }
        }

        outputs = girder_worker.core.run(task, inputs)
        self.assertEqual(outputs['out']['data'], 'a,b,c\n1,2,3\n')

        # Test filepath input with filename specified
        task['inputs'][0]['filename'] = 'file.csv'

        inputs = {
            'file': {
                'data': 'a,b,c\n1,2,3\n',
                'format': 'text',
                'type': 'string'
            }
        }

        outputs = girder_worker.core.run(task, inputs)
        self.assertEqual(outputs['out']['data'], 'a,b,c\n1,2,3\n')
        self.assertEqual(outputs['fname']['data'][-8:], 'file.csv')

    def testHttpIo(self):
        task = {
            'mode': 'python',
            'script': 'y = x + "_suffix"\nfoo="bar"',
            'inputs': [{
                'id': 'x',
                'format': 'text',
                'type': 'string',
                'target': 'filepath',
                'filename': 'override.txt'
            }],
            'outputs': [{
                'id': 'y',
                'format': 'text',
                'type': 'string'
            }, {
                'id': 'foo',
                'format': 'text',
                'type': 'string'
            }]
        }

        inputs = {
            'x': {
                'mode': 'http',
                'url': 'https://foo.com/file.txt',
                'format': 'text',
                'type': 'string'
            }
        }

        outputs = {
            'foo': {
                'mode': 'http',
                'format': 'text',
                'type': 'string',
                'url': 'https://output.com/location.out',
                'headers': {'foo': 'bar'},
                'params': {'queryParam': 'value'},
                'method': 'PUT'
            }
        }

        job_mgr = girder_worker.utils.JobManager(
            True, url='http://jobstatus/')

        received = []
        status_changes = []

        @httmock.all_requests
        def fetchMock(url, request):
            if url.netloc == 'foo.com' and url.scheme == 'https':
                # The input fetch request
                return 'dummy file contents'
            elif url.netloc == 'output.com' and url.path == '/location.out':
                self.assertEqual(url.query, 'queryParam=value')
                received.append(request.body)
                return ''
            elif (url.netloc == 'jobstatus' and url.path == '/' and
                    request.method == 'PUT'):
                status_changes.append(request.body)
                return ''
            else:
                raise Exception('Unexpected url ' + repr(url))

        with httmock.HTTMock(fetchMock):
            # Use user-specified filename
            out = girder_worker.core.run(
                task, inputs=copy.deepcopy(inputs), outputs=outputs,
                cleanup=False, _job_manager=job_mgr, status=JobStatus.RUNNING)

            val = out['y']['data']
            self.assertTrue(val.endswith('override.txt_suffix'))
            path = val[:-7]

            # We should have received 3 status changes
            expected_statuses = [
                JobStatus.FETCHING_INPUT,
                JobStatus.RUNNING,
                JobStatus.PUSHING_OUTPUT
            ]
            self.assertEqual(status_changes, [
                'status=%d' % i for i in expected_statuses])

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
            out = girder_worker.core.run(
                task, inputs=copy.deepcopy(inputs), cleanup=False,
                validate=False, auto_convert=False)
            self.assertTrue(out['y']['data'].endswith('file.txt_suffix'))

            # Download to memory instead of a file (the default target value)
            del task['inputs'][0]['target']
            out = girder_worker.core.run(
                task, inputs=copy.deepcopy(inputs), cleanup=False,
                validate=False, auto_convert=False)
            self.assertEqual(out['y']['data'], 'dummy file contents_suffix')

    def testMagicVariables(self):
        task = {
            'outputs': [{
                'id': '_tempdir',
                'type': 'string',
                'format': 'text'

            }],
            'script': ''
        }

        outputs = girder_worker.core.run(task)
        self.assertTrue('_tempdir' in outputs)
        self.assertRegexpMatches(outputs['_tempdir']['data'], _tmp + '.+')

    def testConvertingStatus(self):
        job_mgr = girder_worker.utils.JobManager(
            True, url='http://jobstatus/')

        status_changes = []

        task = {
            'mode': 'python',
            'script': 'y = x',
            'inputs': [{
                'id': 'x',
                'format': 'tsv',
                'type': 'table'
            }],
            'outputs': [{
                'id': 'y',
                'format': 'tsv',
                'type': 'table'
            }]
        }

        inputs = {
            'x': {
                'mode': 'inline',
                'data': 'a,b,c\nd,e,f\n',
                'type': 'table',
                'format': 'csv'
            }
        }

        outputs = {
            'y': {
                'mode': 'inline',
                'type': 'table',
                'format': 'csv'
            }
        }

        @httmock.all_requests
        def fetchMock(url, request):
            if (url.netloc == 'jobstatus' and url.path == '/' and
                    request.method == 'PUT'):
                status_changes.append(request.body)
                return ''
            else:
                raise Exception('Unexpected url ' + repr(url))

        with httmock.HTTMock(fetchMock):
            girder_worker.core.run(
                task, inputs=inputs, outputs=outputs, _job_manager=job_mgr,
                status=JobStatus.RUNNING)

            # We should have received 3 status changes
            expected_statuses = [
                JobStatus.CONVERTING_INPUT,
                JobStatus.RUNNING,
                JobStatus.CONVERTING_OUTPUT,
                JobStatus.PUSHING_OUTPUT
            ]
            self.assertEqual(status_changes, [
                'status=%d' % i for i in expected_statuses])
