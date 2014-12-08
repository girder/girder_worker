import requests
import sys
import time


class StdoutLogger():
    """
    This class is a context manager that can be used to write log messages to
    Girder by capturing stdout/stderr printed within the context and sending
    them in a rate-limited manner to Girder. This is not threadsafe.
    """
    def __init__(self, url, method, headers, interval=0.5):
        """
        :param interval: Minimum time interval at which to send log updates
        back to Girder over HTTP (seconds).
        :type interval: int or float
        """
        self.method = method
        self.url = url
        self.headers = headers
        self.interval = interval

        self._last = time.time()
        self._pipes = sys.stdout, sys.stderr
        self._buf = ''

        sys.stdout, sys.stderr = self, self

    def __enter__(self):
        return self

    def __exit__(self, excType, excValue, traceback):
        """
        When the context is exited, if we have a non-empty buffer, we flush
        the remaining contents and restore sys.stdout and sys.stderr to their
        previous values.
        """
        self._flush()
        sys.stdout, sys.stderr = self._pipes

    def _flush(self):
        """
        If there are contents in the buffer, send them up to the server. If the
        buffer is empty, this is a no-op.
        """
        if len(self._buf):
            method = getattr(requests, self.method.lower())
            method(self.url, headers=self.headers, data={'log': self._buf})
            self._buf = ''

    def write(self, message):
        """
        This is called when stdout or stderr are written to. Will only flush
        to the server if self.interval seconds have elapsed since last flush.
        """
        self._buf += message
        if time.time() - self._last > self.interval:
            self._flush()
            self._last = time.time()
