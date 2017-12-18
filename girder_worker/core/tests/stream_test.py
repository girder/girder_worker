import httmock
import os
import sys
import threading
import unittest
from . import captureOutput
from girder_worker.core.io import (make_stream_push_adapter,
                                   make_stream_fetch_adapter)
from girder_worker.core.utils import run_process
from six.moves import BaseHTTPServer, socketserver

_iscript = os.path.join(os.path.dirname(__file__), 'stream_input.py')
_oscript = os.path.join(os.path.dirname(__file__), 'stream_output.py')
_pipepath = os.path.join(os.path.dirname(__file__), 'namedpipe')
_socket_port = int(os.environ.get('WORKER_TEST_SOCKET_PORT', 7941))
_server = None
_req_chunks = []


class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_PUT(self):
        while True:
            length = int(self.rfile.readline(), 16)
            if length:
                _req_chunks.append((length, self.rfile.read(length)))
            else:
                break
            self.rfile.readline()  # read the empty line between chunks

        self.close_connection = True
        self.send_response(200, message='received')
        self.end_headers()

    def log_message(self, *args, **kwargs):
        pass  # Override so we don't print to stderr


class ServerThread(object):
    def __init__(self, port):
        self.port = port
        self.httpd = socketserver.TCPServer(('127.0.0.1', self.port), Handler)
        self.thread = threading.Thread(target=self.start, args=(self.httpd,))
        self.thread.start()

    def start(self, httpd):
        httpd.serve_forever()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=10)


def setUpModule():
    global _server
    _server = ServerThread(_socket_port)


def tearDownModule():
    if _server:
        _server.stop()


class TestStream(unittest.TestCase):
    def setUp(self):
        super(TestStream, self).setUp()
        if os.path.exists(_pipepath):
            os.unlink(_pipepath)
        os.mkfifo(_pipepath)

    def tearDown(self):
        super(TestStream, self).tearDown()
        if os.path.exists(_pipepath):
            os.unlink(_pipepath)

    def testOutputStreams(self):
        output_spec = {
            'mode': 'http',
            'method': 'PUT',
            'url': 'http://localhost:%d' % _socket_port
        }

        fd = os.open(_pipepath, os.O_RDONLY | os.O_NONBLOCK)
        adapters = {
            fd: make_stream_push_adapter(output_spec)
        }
        cmd = [sys.executable, _oscript, _pipepath]

        try:
            with captureOutput() as stdpipes:
                run_process(cmd, adapters)
        except Exception:
            print('Stdout/stderr from exception: ')
            print(stdpipes)
            raise
        self.assertEqual(stdpipes, ['start\ndone\n', ''])
        self.assertEqual(len(_req_chunks), 1)
        self.assertEqual(_req_chunks[0], (9, 'a message'))

    def testInputStreams(self):
        input_spec = {
            'mode': 'http',
            'method': 'GET',
            'url': 'http://mockedhost'
        }

        @httmock.urlmatch(netloc='^mockedhost$', method='GET')
        def mock_fetch(url, request):
            return 'hello\nworld'

        adapters = {
            _pipepath: make_stream_fetch_adapter(input_spec)
        }
        cmd = [sys.executable, _iscript, _pipepath]

        try:
            with captureOutput() as stdpipes, httmock.HTTMock(mock_fetch):
                run_process(cmd, input_pipes=adapters)
        except Exception:
            print('Stdout/stderr from exception: ')
            print(stdpipes)
            raise
        self.assertEqual(stdpipes, ['olleh\ndlrow\n', ''])
