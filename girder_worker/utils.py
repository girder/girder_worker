import requests
import time
import sys


class JobStatus(object):
    INACTIVE = 0
    QUEUED = 1
    RUNNING = 2
    SUCCESS = 3
    ERROR = 4
    CANCELED = 5

    FETCHING_INPUT = 820
    CONVERTING_INPUT = 821
    CONVERTING_OUTPUT = 822
    PUSHING_OUTPUT = 823


class JobManager(object):
    """
    This class can be used to write log messages to Girder by capturing
    stdout/stderr printed within the context and sending them in a
    rate-limited manner to Girder. This is not threadsafe since it changes
    the global values of sys.stdout/sys.stderr.

    It also exposes utilities for updating other job fields such as progress
    and status.
    """
    def __init__(self, logPrint, url, method=None, headers=None, interval=0.5,
                 reference=None):
        """
        :param on: Whether print messages should be logged to the job log.
        :type on: bool
        :param url: The job update URL.
        :param method: The HTTP method to use when updating the job.
        :param headers: Optional HTTP header dict
        :param interval: Minimum time interval at which to send log updates
        back to Girder over HTTP (seconds).
        :type interval: int or float
        :param reference: optional reference to store with the job.
        """
        self.logPrint = logPrint
        self.method = method or 'PUT'
        self.url = url
        self.headers = headers or {}
        self.interval = interval
        self.status = None
        self.reference = reference

        self._last = time.time()
        self._buf = ''
        self._progressTotal = None
        self._progressCurrent = None
        self._progressMessage = None

        if logPrint:
            self._pipes = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = self, self

    def _redirectPipes(self, redirect):
        if self.logPrint:
            if redirect:
                sys.stdout, sys.stderr = self, self
            else:
                sys.stdout, sys.stderr = self._pipes

    def _flush(self):
        """
        If there are contents in the buffer, send them up to the server. If the
        buffer is empty, this is a no-op.
        """
        if not self.url:
            return

        if len(self._buf) or self._progressTotal or self._progressMessage or \
                self._progressCurrent is not None:
            self._redirectPipes(False)

            requests.request(
                self.method.upper(), self.url, allow_redirects=True,
                headers=self.headers, data={
                    'log': self._buf,
                    'progressTotal': self._progressTotal,
                    'progressCurrent': self._progressCurrent,
                    'progressMessage': self._progressMessage
                })
            self._buf = ''

            self._redirectPipes(True)

    def flush(self):
        """
        This API call is required to conform to file-like objects,
        but in this case is a no-op to avoid circumventing rate-limiting.
        """
        pass

    def write(self, message, forceFlush=False):
        """
        Append a message to the log for this job. If logPrint is enabled, this
        will be called whenever stdout or stderr is printed to. Otherwise it
        can be called manually and will still perform rate-limited flushing to
        the server.

        :param message: The message to append to the job log.
        :type message: str
        :param forceFlush: Whether to force the write of this event to the
            server. Useful if you don't expect another update for some time.
        :type forceFlush: bool
        """
        if self.logPrint:
            self._pipes[0].write(message)

        if type(message) == unicode:
            message = message.encode('utf8')

        self._buf += message
        if forceFlush or time.time() - self._last > self.interval:
            self._flush()
            self._last = time.time()

    def updateStatus(self, status):
        """
        Update the status field of a job.

        :param status: The status to set on the job.
        :type status: JobStatus
        """
        if not self.url or status is None or status == self.status:
            return

        # Ensure that the logs are flushed before the status is changed
        self._flush()
        self.status = status
        self._redirectPipes(False)
        requests.request(self.method.upper(), self.url, headers=self.headers,
                         data={'status': status}, allow_redirects=True)
        self._redirectPipes(True)

    def updateProgress(self, total=None, current=None, message=None,
                       forceFlush=False):
        """
        Update the progress information about a job.

        :param total: The total progress value, or None to leave the same.
        :type total: int, float, or None
        :param current: The current progress value, or None to leave the same.
        :type current: int, float, or None
        :param message: Progress message to set, or None to leave the same.
        :type message: str or None
        :param forceFlush: Whether to force the write of this event to the
            server. Useful if you don't expect another update for some time.
        :type forceFlush: bool
        """
        if total is not None:
            self._progressTotal = total
        if current is not None:
            self._progressCurrent = current
        if message is not None:
            self._progressMessage = message

        if forceFlush or time.time() - self._last > self.interval:
            self._flush()
            self._last = time.time()
