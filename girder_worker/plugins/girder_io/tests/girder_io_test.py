import copy
import json
import httmock
import mock
import os
import girder_worker
import girder_worker.tasks
import shutil
import unittest

_tmp = None


def setUpModule():
    global _tmp
    _tmp = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'tmp', 'girder_io')
    girder_worker.config.set('girder_worker', 'tmp_root', _tmp)

    if os.path.isdir(_tmp):
        shutil.rmtree(_tmp)


def tearDownModule():
    if os.path.isdir(_tmp):
        shutil.rmtree(_tmp)


class TestGirderIo(unittest.TestCase):

    def setUp(self):
        self.task = {
            'inputs': [{'name': 'input', 'type': 'string', 'format': 'text'}],
            'outputs': [{'name': 'out', 'type': 'string', 'format': 'text'}],
            'script': 'out = input',
            'mode': 'python'
        }

    def test_girder_io(self):
        file_uploaded = []
        file_downloaded = []
        upload_initialized = []

        @httmock.all_requests
        def girder_mock(url, request):
            api_root = '/girder/api/v1'
            self.assertEqual(request.headers['Girder-Token'], 'foo')
            self.assertEqual(url.scheme, 'http')
            self.assertTrue(url.path.startswith(api_root), url.path)
            self.assertEqual(url.netloc, 'localhost:8080')

            if url.path == api_root + '/item/item_id/files':
                return json.dumps([{
                    'name': 'test.txt',
                    '_id': 'file_id',
                    'created': '2000-01-01 00:00:00',
                    'size': 13
                }])
            if url.path == api_root + '/item/new_item_id/files':
                return '[]'
            if url.path == api_root + '/file/file_id/download':
                file_downloaded.append(1)
                return 'file_contents'
            if url.path == api_root + '/file' and request.method == 'POST':
                upload_initialized.append(1)
                return json.dumps({
                    '_id': 'upload_id',
                    'created': '2000-01-01 00:00:00',
                })
            if url.path == api_root + '/file/chunk' and request.method == 'POST':
                file_uploaded.append(1)
                return json.dumps({
                    '_id': 'new_file_id',
                    'created': '2000-01-01 00:00:00',
                    'name': 'test.txt'
                })
            if url.path == api_root + '/describe' and request.method == 'GET':
                return json.dumps({
                    'info': {'version': '2.2.0'}
                })
            raise Exception('Unexpected %s request to %s.' % (request.method, url.path))

        inputs = {
            'input': {
                'mode': 'girder',
                'host': 'localhost',
                'scheme': 'http',
                'port': 8080,
                'api_root': '/girder/api/v1',
                'resource_type': 'item',
                'id': 'item_id',
                'type': 'string',
                'format': 'text',
                'name': 'test.txt',
                'token': 'foo'
            }
        }

        with httmock.HTTMock(girder_mock):
            outputs = girder_worker.tasks.run(
                self.task, inputs=inputs, outputs=None, cleanup=False)
            path = outputs['out']['data']
            self.assertTrue(os.path.isfile(path), path + ' does not exist')
            with open(path) as f:
                self.assertEqual(f.read(), 'file_contents')
            shutil.rmtree(os.path.dirname(path))  # clean tmp dir

            # test diskcache
            self.assertEqual(file_downloaded, [1])
            girder_worker.config.set('girder_io', 'diskcache_enabled', '1')
            girder_worker.config.set('girder_io', 'diskcache_directory', _tmp)
            girder_worker.tasks.run(self.task, inputs=inputs, outputs=None)
            self.assertEqual(file_downloaded, [1, 1])
            girder_worker.tasks.run(self.task, inputs=inputs, outputs=None)
            self.assertEqual(file_downloaded, [1, 1])

            # Now test pushing to girder
            del inputs['input']['data']
            outputs = {
                'out': {
                    'mode': 'girder',
                    'host': 'localhost',
                    'scheme': 'http',
                    'port': 8080,
                    'api_root': '/girder/api/v1',
                    'parent_type': 'folder',
                    'parent_id': 'some_folder_id',
                    'format': 'text',
                    'type': 'string',
                    'token': 'foo'
                }
            }

            girder_worker.tasks.run(self.task, inputs=inputs, outputs=outputs)
            self.assertEqual(file_uploaded, [1])
            self.assertEqual(upload_initialized, [1])

    def test_memory_targets(self):
        upload_initialized = []
        chunk_sent = []

        @httmock.all_requests
        def girder_mock(url, request):
            api_root = '/girder/api/v1'
            self.assertEqual(request.headers['Girder-Token'], 'foo')
            self.assertEqual(url.scheme, 'http')
            self.assertTrue(url.path.startswith(api_root), url.path)
            self.assertEqual(url.netloc, 'localhost:8080')

            if url.path == api_root + '/item/item_id/files':
                return json.dumps([{
                    'name': 'test.txt',
                    '_id': 'file_id',
                    'created': '2000-01-01 00:00:00',
                    'size': 13
                }])
            if url.path == api_root + '/item/new_item_id/files':
                return '[]'
            if url.path == api_root + '/file/file_id/download':
                return 'file_contents'
            if url.path == api_root + '/file' and request.method == 'POST':
                upload_initialized.append(1)
                return json.dumps({
                    '_id': 'upload_id',
                    'created': '2000-01-01 00:00:00',
                })
            if url.path == api_root + '/file/chunk' and request.method == 'POST':
                self.assertTrue('file_contents' in request.body)
                chunk_sent.append(1)
                return json.dumps({
                    '_id': 'new_file_id',
                    'created': '2000-01-01 00:00:00',
                    'name': 'test.txt'
                })
            if url.path == api_root + '/describe' and request.method == 'GET':
                return json.dumps({
                    'info': {'version': '2.2.0'}
                })
            raise Exception('Unexpected %s request to %s.' % (request.method, url.path))

        inputs = {
            'input': {
                'mode': 'girder',
                'host': 'localhost',
                'scheme': 'http',
                'port': 8080,
                'api_root': '/girder/api/v1',
                'resource_type': 'item',
                'id': 'item_id',
                'type': 'string',
                'format': 'text',
                'name': 'test.txt',
                'token': 'foo'
            }
        }

        outputs = {
            'out': {
                'mode': 'girder',
                'host': 'localhost',
                'scheme': 'http',
                'port': 8080,
                'api_root': '/girder/api/v1',
                'parent_type': 'item',
                'parent_id': 'item_id',
                'format': 'text',
                'type': 'string',
                'token': 'foo',
                'name': 'hello_world.txt'
            }
        }

        task = {
            'inputs': [{
                'name': 'input',
                'type': 'string',
                'format': 'text',
                'target': 'memory'
            }],
            'outputs': [{
                'name': 'out',
                'type': 'string',
                'format': 'text',
                'target': 'memory'
            }],
            'script': 'out = input',
            'mode': 'python'
        }

        with httmock.HTTMock(girder_mock):
            girder_worker.tasks.run(task, inputs=inputs, outputs=outputs)
            self.assertEqual(chunk_sent, [1])
            self.assertEqual(upload_initialized, [1])

    def test_girder_io_params(self):
        task = {
            'inputs': [{
                'name': 'input',
                'type': 'string',
                'format': 'text',
                'target': 'memory'
            }],
            'outputs': [{
                'name': 'out',
                'type': 'string',
                'format': 'text',
                'target': 'memory'
            }],
            'script': 'out = input',
            'mode': 'python'
        }

        @httmock.all_requests
        def girder_mock(url, request):
            api_root = self.api_root
            self.assertEqual(request.headers['Girder-Token'], 'foo')
            self.assertEqual(url.scheme, self.scheme)
            self.assertTrue(url.path.startswith(api_root), url.path)
            self.assertEqual(url.netloc, self.netloc)

            if url.path == api_root + '/item/item_id/files':
                return json.dumps([{
                    'name': 'test.txt',
                    '_id': 'file_id',
                    'created': '2000-01-01 00:00:00',
                    'size': 13
                }])
            if url.path == api_root + '/item/new_item_id/files':
                return '[]'
            if url.path == api_root + '/file/file_id/download':
                return 'file_contents'
            if url.path == api_root + '/file' and request.method == 'POST':
                return json.dumps({
                    '_id': 'upload_id',
                    'created': '2000-01-01 00:00:00',
                })
            if url.path == api_root + '/file/chunk' and request.method == 'POST':
                self.assertTrue('file_contents' in request.body)
                return json.dumps({
                    '_id': 'new_file_id',
                    'created': '2000-01-01 00:00:00',
                    'name': 'test.txt'
                })
            if url.path == api_root + '/describe' and request.method == 'GET':
                return json.dumps({
                    'info': {'version': '2.2.0'}
                })
            raise Exception('Unexpected %s request to %s.' % (request.method, url.path))

        # Test that api_url overrides the other values
        self.api_root = '/foo/bar/api'
        self.netloc = 'hello.com:1234'
        self.scheme = 'https'

        inputs = {
            'input': {
                'mode': 'girder',
                'api_url': 'https://hello.com:1234/foo/bar/api',
                'token': 'foo',
                'host': 'wronghost',
                'id': 'item_id',
                'name': 'test.txt',
                'resource_type': 'item',
                'port': 5678,
                'api_root': '/wrong/api/root',
                'scheme': 'http',
                'format': 'text',
                'type': 'string'
            }
        }

        outputs = {
            'out': {
                'mode': 'girder',
                'api_url': 'https://hello.com:1234/foo/bar/api',
                'token': 'foo',
                'host': 'wronghost',
                'port': 5678,
                'api_root': '/wrong/api/root',
                'scheme': 'http',
                'name': 'out.txt',
                'format': 'text',
                'type': 'string',
                'parent_id': 'abcd',
                'parent_type': 'folder'
            }
        }

        with httmock.HTTMock(girder_mock):
            outputs = girder_worker.tasks.run(
                copy.deepcopy(task), inputs=inputs, outputs=outputs)

            # Test default values for scheme, host, and port
            self.scheme = 'http'
            self.netloc = 'wronghost:80'
            self.api_root = '/api/v1'

            inputs = {
                'input': {
                    'mode': 'girder',
                    'token': 'foo',
                    'host': 'wronghost',
                    'id': 'item_id',
                    'name': 'test.txt',
                    'resource_type': 'item',
                    'format': 'text',
                    'type': 'string'
                }
            }

            girder_worker.tasks.run(copy.deepcopy(task), inputs=inputs)

    def test_fetch_parent(self):
        task = {
            'inputs': [{
                'name': 'input',
                'type': 'string',
                'format': 'text',
                'target': 'filepath'
            }],
            'outputs': [{
                'name': 'out',
                'type': 'string',
                'format': 'text'
            }],
            'script': 'out = input',
            'mode': 'python',
            'cleanup': False
        }

        self.api_root = '/foo/bar/api'
        self.netloc = 'hello.com:1234'
        self.scheme = 'https'

        inputs = {
            'input': {
                'mode': 'girder',
                'api_url': 'https://hello.com:1234/foo/bar/api',
                'id': 'file2_id',
                'name': 'other_file.txt',
                'resource_type': 'file',
                'fetch_parent': True
            }
        }

        file1_info = {
            '_id': 'file1_id',
            'created': '2000-01-01 00:00:00',
            'name': 'text.txt',
            'itemId': 'item_id',
            'size': 13
        }

        file2_info = {
            '_id': 'file2_id',
            'created': '2000-01-01 00:00:00',
            'name': 'other_file.txt',
            'itemId': 'item_id',
            'size': 3
        }

        parent_item = {
            '_id': 'item_id',
            'name': 'parent_item'
        }

        @httmock.all_requests
        def girder_mock(url, request):
            api_root = self.api_root

            if url.path == api_root + '/file/file1_id':  # fetch file info
                return json.dumps(file1_info)
            if url.path == api_root + '/file/file2_id':  # fetch file info
                return json.dumps(file2_info)
            if url.path == api_root + '/item/item_id':  # fetch item info
                return json.dumps(parent_item)
            if url.path == api_root + '/item/item_id/files':  # list parent
                return json.dumps([file1_info, file2_info])
            if url.path == api_root + '/file/file1_id/download':
                return 'file_contents'
            if url.path == api_root + '/file/file2_id/download':
                return 'foo'
            if url.path == api_root + '/describe' and request.method == 'GET':
                return json.dumps({
                    'info': {'version': '2.2.0'}
                })
            raise Exception('Unexpected %s request to %s.' % (request.method, url.path))

        with httmock.HTTMock(girder_mock):
            outputs = girder_worker.tasks.run(task, inputs=inputs,
                                              validate=False,
                                              auto_convert=False,
                                              cleanup=False)
            self.assertIn('out', outputs)
            path = outputs['out']['data']
            parent = os.path.dirname(path)
            file1_path = os.path.join(parent, 'text.txt')
            self.assertTrue(os.path.isfile(path))
            self.assertTrue(os.path.isfile(file1_path))
            self.assertEqual(os.path.basename(path), 'other_file.txt')
            self.assertEqual(os.path.basename(parent), 'parent_item')
            with open(path, 'rb') as fd:
                self.assertEqual(fd.read(), 'foo')
            with open(file1_path, 'rb') as fd:
                self.assertEqual(fd.read(), 'file_contents')

    def test_direct_path(self):
        task = {
            'inputs': [{
                'name': 'input',
                'type': 'string',
                'format': 'text',
                'target': 'filepath'
            }],
            'outputs': [{
                'name': 'out',
                'type': 'string',
                'format': 'text'
            }],
            'script': 'out = input',
            'mode': 'python',
            'cleanup': False
        }

        inputs = {
            'input': {
                'mode': 'girder',
                'api_url': 'https://hello.com:1234/foo/bar/api',
                'id': 'file1_id',
                'name': 'text.txt',
                'resource_type': 'file',
                'direct_path': __file__
            }
        }

        @httmock.all_requests
        def girder_mock(url, request):
            raise Exception('Unexpected %s request to %s.' % (request.method, url.path))

        with httmock.HTTMock(girder_mock):
            outputs = girder_worker.tasks.run(task, inputs=inputs,
                                              validate=False,
                                              auto_convert=False,
                                              cleanup=False)
            self.assertIn('out', outputs)
            path = outputs['out']['data']
            self.assertEqual(path, __file__)

    def test_metadata_output(self):
        task = {
            'inputs': [{'name': 'input', 'type': 'string', 'format': 'text'}],
            'outputs': [{'name': 'out', 'type': 'string', 'format': 'text', 'target': 'memory'}],
            'script': 'out = input',
            'mode': 'python'
        }

        inputs = {
            'input': {
                'mode': 'inline',
                'data': json.dumps({
                    'hello': 'world'
                })
            }
        }

        # Test adding an output as metadata on an item
        outputs = {
            'out': {
                'mode': 'girder',
                'as_metadata': True,
                'item_id': 'my_item_id',
                'api_url': 'https://hello.com:1234/foo/bar/api',
                'token': 'foo'
            }
        }

        metadata_updates = []
        file_creates = []

        @httmock.all_requests
        def girder_mock(url, request):
            api_root = '/foo/bar/api'

            if url.path == api_root + '/file/chunk' and request.method == 'POST':
                return json.dumps({
                    '_id': 'my_file_id',
                    'itemId': 'my_item_id',
                    'size': 9,
                    'name': 'file name'
                })
            if url.path == api_root + '/file' and request.method == 'POST':
                file_creates.append(request)
                return json.dumps({
                    '_id': 'my_file_id',
                    'offset': 0
                })
            if url.path == api_root + '/item/my_item_id/metadata':
                metadata_updates.append(json.loads(request.body))
                return '{}'  # we don't look at the return value for the moment
            if url.path == api_root + '/describe' and request.method == 'GET':
                return json.dumps({
                    'info': {'version': '2.2.0'}
                })
            if url.path == api_root + '/item' and request.method == 'POST':
                return json.dumps({
                    '_id': 'my_item_id'
                })
            raise Exception('Unexpected %s request to %s.' % (request.method, url.path))

        with httmock.HTTMock(girder_mock):
            girder_worker.tasks.run(
                task, inputs=inputs, outputs=outputs, validate=False, auto_convert=False)

            self.assertEqual(metadata_updates, [{
                'hello': 'world'
            }])

        # Test adding metadata on an item output
        metadata_updates = []

        inputs['input'] = {
            'mode': 'inline',
            'data': 'file data'
        }

        outputs['out'] = {
            'mode': 'girder',
            'metadata': {
                'some': 'other',
                'metadata': 'values'
            },
            'parent_id': 'my_folder_id',
            'parent_type': 'folder',
            'api_url': 'https://hello.com:1234/foo/bar/api',
            'name': 'my item',
            'token': 'foo'
        }

        with httmock.HTTMock(girder_mock):
            girder_worker.tasks.run(
                task, inputs=inputs, outputs=outputs, validate=False, auto_convert=False)

            self.assertEqual(len(file_creates), 1)
            self.assertEqual(metadata_updates, [{
                'some': 'other',
                'metadata': 'values'
            }])

        # Test filepath target metadata output
        task['outputs'][0]['target'] = 'filepath'
        path = os.path.join(_tmp, 'out.txt')
        with open(path, 'w') as fd:
            json.dump({
                'filepath': 'test'
            }, fd)

        inputs['input'] = {
            'mode': 'inline',
            'data': path
        }

        outputs['out'] = {
            'mode': 'girder',
            'as_metadata': True,
            'parent_id': 'my_folder_id',
            'parent_type': 'folder',
            'api_url': 'https://hello.com:1234/foo/bar/api',
            'token': 'foo'
        }

        metadata_updates = []

        with httmock.HTTMock(girder_mock):
            girder_worker.tasks.run(
                task, inputs=inputs, outputs=outputs, validate=False, auto_convert=False)

            self.assertEqual(metadata_updates, [{'filepath': 'test'}])

    @mock.patch('girder_client.GirderClient.upload')
    def test_directory_output(self, upload_mock):
        out_dir = os.path.join(_tmp, 'out_dir')
        sub_dir = os.path.join(out_dir, 'sub_dir')
        try:
            os.makedirs(sub_dir)
        except OSError:
            if not os.path.isdir(sub_dir):
                raise

        with open(os.path.join(sub_dir, 'file.txt'), 'w') as fd:
            fd.write('hello')

        task = {
            'inputs': [{'name': 'input'}],
            'outputs': [{'name': 'out', 'target': 'filepath'}],
            'script': 'out = input',
            'mode': 'python'
        }

        inputs = {
            'input': {
                'mode': 'inline',
                'data': out_dir
            }
        }

        outputs = {
            'out': {
                'mode': 'girder',
                'parent_id': 'my_folder_id',
                'parent_type': 'folder',
                'api_url': 'https://hello.com:1234/foo/bar/api',
                'name': 'my folder',
                'token': 'foo',
                'reference': 'my reference'
            }
        }

        girder_worker.tasks.run(
            task, inputs=inputs, outputs=outputs, validate=False, auto_convert=False)
        self.assertEqual(len(upload_mock.mock_calls), 1)
        _, args, kwargs = upload_mock.mock_calls[0]

        self.assertEqual(args[0], out_dir)
        self.assertEqual(kwargs['reference'], 'my reference')


if __name__ == '__main__':
    unittest.main()
