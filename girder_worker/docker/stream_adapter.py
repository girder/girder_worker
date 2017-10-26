from girder_worker.core.utils import StreamPushAdapter
import struct


class DockerStreamPushAdapter(StreamPushAdapter):
    """
    An adapter that reads a docker stream. The format is a Header and a Payload (frame).

    Where header has the following format:
        header := [8]byte{STREAM_TYPE, 0, 0, 0, SIZE1, SIZE2, SIZE3, SIZE4}

    We want to read the header to get the size of the payload, read the payload
    and forward it on to another adapter.

    """
    def __init__(self, adapter):
        self._adapter = adapter
        self._reset()

    def _reset(self):
        self._header = ''
        self._header_bytes_read = 0
        self._payload_bytes_read = 0
        self._payload_size = None

    def _read_header(self):
        """
        Read the header or part of the header. When the head has been read, the
        payload size is decodeded and returned, otherwise return None.
        """
        bytes_to_read = min(8 - self._header_bytes_read, self._data_length-self._data_offset)
        self._header += self._data[self._data_offset:self._data_offset+bytes_to_read]
        self._data_offset += bytes_to_read
        self._header_bytes_read += bytes_to_read

        if self._header_bytes_read == 8:
            _, payload_size = struct.unpack('>BxxxL', self._header)

            return payload_size

    def _read_payload(self):
        """
        Read the payload or part of the payload. The data is written directly to
        the wrapped adapter.
        """
        bytes_to_read = min(self._payload_size - self._payload_bytes_read,
                            self._data_length-self._data_offset)
        self._adapter.write(self._data[self._data_offset:self._data_offset+bytes_to_read])
        self._data_offset += bytes_to_read
        self._payload_bytes_read += bytes_to_read

    def write(self, data):
        self._data = data
        self._data_length = len(data)
        self._data_offset = 0

        # While we still have data iterate over it
        while self._data_length > self._data_offset:
            # We are reading the header
            if self._header_bytes_read < 8:
                self._payload_size = self._read_header()

            # We are reading the payload
            if self._payload_size and self._payload_bytes_read < self._payload_size:
                self._read_payload()

            # We are done with this payload
            if self._payload_size == self._payload_bytes_read:
                self._reset()

    def close(self):
        self._adapter.close()
