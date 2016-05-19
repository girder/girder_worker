import httplib
import os
import re
import requests
import ssl
import urlparse

from girder_worker.utils import StreamPushAdapter


class HttpStreamPushAdapter(StreamPushAdapter):
    def __init__(self, output_spec):
        """
        Uses HTTP chunked transfer-encoding to stream a request body to a
        server. Unfortunately requests does not support hooking into this logic
        easily, so we use the lower-level httplib module.
        """
        super(HttpStreamPushAdapter, self).__init__(output_spec)

        parts = urlparse.urlparse(output_spec['url'])
        if parts.scheme == 'https':
            ssl_context = ssl.create_default_context()
            conn = httplib.HTTPSConnection(parts.netloc, context=ssl_context)
        else:
            conn = httplib.HTTPConnection(parts.netloc)

        conn.putrequest(output_spec.get('method', 'POST').upper(),
                        parts.path, skip_accept_encoding=True)

        for header, value in output_spec.get('headers', {}).items():
            conn.putheader(header, value)

        conn.putheader('Transfer-Encoding', 'chunked')
        conn.endheaders()  # This actually flushes the headers to the server

        self.conn = conn

    def write(self, buf):
        """
        Write a chunk of data to the output stream in accordance with the
        chunked transfer encoding protocol.
        """
        try:
            self.conn.send(hex(len(buf))[2:].encode('utf-8'))
            self.conn.send(b'\r\n')
            self.conn.send(buf)
            self.conn.send(b'\r\n')
        except Exception:
            self.conn.close()
            raise

    def close(self):
        """
        Close the output stream. Called after the last data is sent.
        """
        try:
            self.conn.send(b'0\r\n\r\n')
            resp = self.conn.getresponse(buffering=True)
            if resp.status >= 300 and resp.status < 400:
                raise Exception('Redirects are not supported for streaming '
                                'requests at this time. %d to Location: %s' % (
                                    resp.status, resp.getheader('Location')))
            if resp.status >= 400:
                raise Exception(
                    'HTTP stream output to %s failed with status %d. Response '
                    'was: %s' % (
                        self.output_spec['url'], resp.status, resp.read()))
        finally:
            self.conn.close()


def _readFilenameFromResponse(request, url):
    """
    This helper will derive a filename from the HTTP response, first attempting
    to use the content disposition header, otherwise falling back to the last
    token of the URL.
    """
    match = re.search('filename="(.*)"',
                      request.headers.get('Content-Disposition', ''))

    if match is None:
        return [t for t in url.split('/') if t][-1]
    else:
        return match.group(1)


def fetch(spec, **kwargs):
    """
    Downloads an input file via HTTP using requests.
    """
    if 'url' not in spec:
        raise Exception('No URL specified for HTTP input.')
    taskInput = kwargs.get('task_input', {})
    target = taskInput.get('target', 'memory')
    url = spec['url']
    method = spec.get('method', 'GET').upper()
    request = requests.request(method, url, headers=spec.get('headers', {}),
                               params=spec.get('params', {}),
                               stream=True, allow_redirects=True)

    try:
        request.raise_for_status()
    except Exception:
        print 'HTTP fetch failed (%s). Response: %s' % (url, request.text)
        raise

    if target == 'filepath':
        tmpDir = kwargs['_tempdir']

        if 'filename' in taskInput:
            filename = taskInput['filename']
        else:
            filename = _readFilenameFromResponse(request, url)

        path = os.path.join(tmpDir, filename)

        total = 0
        maxSize = spec.get('maxSize')

        with open(path, 'wb') as out:
            for buf in request.iter_content(65536):
                length = len(buf)
                if maxSize and length + total > maxSize:
                    raise Exception(
                        'Exceeded max download size of %d bytes.' % maxSize)
                out.write(buf)
                total += length

        return path
    elif target == 'memory':
        return ''.join(request.iter_content(65536))
    else:
        raise Exception('Invalid HTTP fetch target: ' + target)


def push(data, spec, **kwargs):
    task_output = kwargs.get('task_output', {})
    target = task_output.get('target', 'memory')

    url = spec['url']
    method = spec.get('method', 'POST').upper()

    if target == 'filepath':
        with open(data, 'rb') as fd:
            request = requests.request(
                method, url, headers=spec.get('headers', {}), data=fd,
                allow_redirects=True)
    elif target == 'memory':
        request = requests.request(
            method, url, headers=spec.get('headers', {}), data=data,
            allow_redirects=True)
    else:
        raise Exception('Invalid HTTP fetch target: ' + target)

    try:
        request.raise_for_status()
    except Exception:
        print 'HTTP push failed (%s). Response: %s' % (url, request.text)
        raise
