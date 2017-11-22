import six

from . import StreamReader


class GirderFileStreamReader(StreamReader):
    def __init__(self, client, file_id):
        super(GirderFileStreamReader, self).__init__()
        self._client = client
        self._file_id = file_id
        self._iter = None

    def read(self, buf_len):
        """
        Implementation note: due to a constraint of the requests library, the
        buf_len that is used the first time this method is called will cause
        all future requests to ``read`` to have the same ``buf_len`` even if
        a different ``buf_len`` is passed in on subsequent requests.
        """
        if self._iter is None:  # lazy load response body iterator
            self._iter = self._client.downloadFileAsIterator(self._file_id, buf_len)

        try:
            return six.next(self._iter)
        except StopIteration:
            return b''
