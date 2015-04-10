import contextlib
import functools
import os
import requests
import romanesco
import shutil
import sys
import tempfile
import time
import traceback
import zipfile


class JobStatus(object):
    INACTIVE = 0
    QUEUED = 1
    RUNNING = 2
    SUCCESS = 3
    ERROR = 4
    CANCELED = 5


class JobManager(object):
    """
    This class is a context manager that can be used to write log messages to
    Girder by capturing stdout/stderr printed within the context and sending
    them in a rate-limited manner to Girder. This is not threadsafe since it
    changes the global values of sys.stdout/sys.stderr.

    It also exposes utilities for updating other job fields such as progress
    and status.
    """
    def __init__(self, logPrint, url, method=None, headers=None, interval=0.5):
        """
        :param on: Whether print messages should be logged to the job log.
        :type on: bool
        :param url: The job update URL.
        :param method: The HTTP method to use when updating the job.
        :param headers: Optional HTTP header dict
        :param interval: Minimum time interval at which to send log updates
        back to Girder over HTTP (seconds).
        :type interval: int or float
        """
        self.logPrint = logPrint
        self.method = method or 'PUT'
        self.url = url
        self.headers = headers or {}
        self.interval = interval

        self._last = time.time()
        self._buf = ''
        self._progressTotal = None
        self._progressCurrent = None
        self._progressMessage = None

        if logPrint:
            self._pipes = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = self, self

    def __enter__(self):
        return self

    def __exit__(self, excType, excValue, tb):
        """
        When the context is exited, if we have a non-empty buffer, we flush
        the remaining contents and restore sys.stdout and sys.stderr to their
        previous values. We also set the job status to ERROR if we exited the
        context with an exception, or SUCCESS otherwise.
        """
        if excType:
            msg = '%s: %s\n%s' % (
                excType, excValue, ''.join(traceback.format_tb(tb)))

            self.write(msg)
            self.updateStatus(JobStatus.ERROR)
        else:
            self.updateStatus(JobStatus.SUCCESS)

        self._flush()

        if self.logPrint:
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
            httpMethod = getattr(requests, self.method.lower())

            httpMethod(self.url, headers=self.headers, data={
                'log': self._buf,
                'progressTotal': self._progressTotal,
                'progressCurrent': self._progressCurrent,
                'progressMessage': self._progressMessage
            })
            self._buf = ''

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
        httpMethod = getattr(requests, self.method.lower())
        httpMethod(self.url, headers=self.headers, data={'status': status})

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


def toposort(data):
    """
    General-purpose topological sort function. Dependencies are expressed as a
    dictionary whose keys are items and whose values are a set of dependent
    items. Output is a list of sets in topological order. This is a generator
    function that returns a sequence of sets in topological order.

    :param data: The dependency information.
    :type data: dict
    :returns: Yields a list of sorted sets representing the sorted order.
    """
    if not data:
        return

    # Ignore self dependencies.
    for k, v in data.items():
        v.discard(k)

    # Find all items that don't depend on anything.
    extra = functools.reduce(
        set.union, data.itervalues()) - set(data.iterkeys())
    # Add empty dependences where needed
    data.update({item: set() for item in extra})

    # Perform the toposort.
    while True:
        ordered = set(item for item, dep in data.iteritems() if not dep)
        if not ordered:
            break
        yield ordered
        data = {item: (dep - ordered)
                for item, dep in data.iteritems() if item not in ordered}
    # Detect any cycles in the dependency graph.
    if data:
        raise Exception('Cyclic dependencies detected:\n%s' % '\n'.join(
                        repr(x) for x in data.iteritems()))


@contextlib.contextmanager
def tmpdir(cleanup=True):
    # Make the temp dir underneath tmp_root config setting
    root = os.path.abspath(romanesco.config.get('romanesco', 'tmp_root'))
    try:
        os.makedirs(root)
    except OSError:
        if not os.path.isdir(root):
            raise
    path = tempfile.mkdtemp(dir=root)

    yield path

    # Cleanup the temp dir
    if cleanup and os.path.isdir(path):
        shutil.rmtree(path)


def with_tmpdir(fn):
    """
    This function is provided as a convenience to allow use as a decorator of
    a function rather than using "with tmpdir()" around the whole function
    body. It passes the generated temp dir path into the function as the
    special kwarg "_tmp_dir".
    """
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        cleanup = kwargs.get('cleanup', True)
        with tmpdir(cleanup=cleanup) as tmp_dir:
            kwargs['_tmp_dir'] = tmp_dir
            return fn(*args, **kwargs)
    return wrapped


def extractZip(path, dest, flatten=False):
    """
    Extract a zip file, optionally flattening it into a single directory.
    """
    try:
        os.makedirs(dest)
    except OSError:
        if not os.path.exists(dest):
            raise

    with zipfile.ZipFile(path) as zf:
        if flatten:
            for name in zf.namelist():
                out = os.path.join(dest, os.path.basename(name))
                with open(out, 'wb') as ofh:
                    with zf.open(name) as ifh:
                        while True:
                            buf = ifh.read(65536)
                            if buf:
                                ofh.write(buf)
                            else:
                                break
        else:
            zf.extractall(output)
