import httplib
import os
import re
import requests
import six
import ssl
import urlparse

from girder_worker.core.utils import StreamFetchAdapter, StreamPushAdapter


class HttpStreamFetchAdapter(StreamFetchAdapter):
    def __init__(self, input_spec):
        super(HttpStreamFetchAdapter, self).__init__(input_spec)

        self._iter = None  # will be lazily created

    def read(self, buf_len):
        """
        Implementation note: due to a constraint of the requests library, the
        buf_len that is used the first time this method is called will cause
        all future requests to ``read`` to have the same ``buf_len`` even if
        a different ``buf_len`` is passed in on subsequent requests.
        """
        if self._iter is None:  # lazy load response body iterator
            method = self.input_spec.get('method', 'GET').upper()
            headers = self.input_spec.get('headers', {})
            params = self.input_spec.get('params', {})
            req = requests.request(
                method, self.input_spec['url'], headers=headers, params=params,
                stream=True, allow_redirects=True)
            req.raise_for_status()  # we have the response headers already
            self._iter = req.iter_content(buf_len, decode_unicode=False)

        try:
            return six.next(self._iter)
        except StopIteration:
            return b''


class HttpStreamPushAdapter(StreamPushAdapter):
    def __init__(self, output_spec):
        """
        Uses HTTP chunked transfer-encoding to stream a request body to a
        server. Unfortunately requests does not support hooking into this logic
        easily, so we use the lower-level httplib module.
        """
        super(HttpStreamPushAdapter, self).__init__(output_spec)
        self._closed = False

        parts = urlparse.urlparse(output_spec['url'])
        if parts.scheme == 'https':
            ssl_context = ssl.create_default_context()
            conn = httplib.HTTPSConnection(parts.netloc, context=ssl_context)
        else:
            conn = httplib.HTTPConnection(parts.netloc)

        try:
            conn.putrequest(output_spec.get('method', 'POST').upper(),
                            parts.path, skip_accept_encoding=True)

            for header, value in output_spec.get('headers', {}).items():
                conn.putheader(header, value)

            conn.putheader('Transfer-Encoding', 'chunked')
            conn.endheaders()  # This actually flushes the headers to the server
        except Exception:
            print('HTTP connection to "%s" failed.' % output_spec['url'])
            conn.close()
            raise

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
            resp = self.conn.getresponse()
            print('Exception while sending HTTP chunk to %s, status was %s, '
                  'message was:\n%s' % (self.output_spec['url'], resp.status,
                                        resp.read()))
            self.conn.close()
            self._closed = True
            raise

    def close(self):
        """
        Close the output stream. Called after the last data is sent.
        """
        if self._closed:
            return

        try:
            self.conn.send(b'0\r\n\r\n')
            resp = self.conn.getresponse()
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


def _read_filename_from_resp(request, url):
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
    task_input = kwargs.get('task_input', {})
    target = task_input.get('target', 'memory')
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

        if 'filename' in task_input:
            filename = task_input['filename']
        else:
            filename = _read_filename_from_resp(request, url)

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
                params=spec.get('params', {}), allow_redirects=True)
    elif target == 'memory':
        request = requests.request(
            method, url, headers=spec.get('headers', {}), data=data,
            params=spec.get('params', {}), allow_redirects=True)
    else:
        raise Exception('Invalid HTTP fetch target: ' + target)

    try:
        request.raise_for_status()
    except Exception:
        print 'HTTP push failed (%s). Response: %s' % (url, request.text)
        raise
