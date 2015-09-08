import contextlib
import functools
import imp
import os
import requests
import romanesco
import select
import shutil
import subprocess
import sys
import tempfile
import time
import traceback


class JobStatus(object):
    INACTIVE = 0
    QUEUED = 1
    RUNNING = 2
    SUCCESS = 3
    ERROR = 4
    CANCELED = 5


class TerminalColor(object):
    """
    Provides a set of values that can be used to color text in the terminal.
    """
    ERROR = '\033[1;91m'
    SUCCESS = '\033[32m'
    WARNING = '\033[1;33m'
    INFO = '\033[35m'
    ENDC = '\033[0m'

    @staticmethod
    def _color(tag, text):
        return ''.join([tag, text, TerminalColor.ENDC])

    @staticmethod
    def error(text):
        return TerminalColor._color(TerminalColor.ERROR, text)

    @staticmethod
    def success(text):
        return TerminalColor._color(TerminalColor.SUCCESS, text)

    @staticmethod
    def warning(text):
        return TerminalColor._color(TerminalColor.WARNING, text)

    @staticmethod
    def info(text):
        return TerminalColor._color(TerminalColor.INFO, text)


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
        self.updateStatus(JobStatus.RUNNING)
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
        self._redirectPipes(False)

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
        if not self.url:
            return

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

    try:
        yield path
    finally:
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
        if '_tmp_dir' in kwargs:
            return fn(*args, **kwargs)

        cleanup = kwargs.get('cleanup', True)
        with tmpdir(cleanup=cleanup) as tmp_dir:
            kwargs['_tmp_dir'] = tmp_dir
            return fn(*args, **kwargs)
    return wrapped


class PluginNotFoundException(Exception):
    pass


def load_plugins(plugins, paths, ignore_errors=False, quiet=False):
    """
    Enable a list of plugins.

    :param plugins: The plugins to enable.
    :type plugins: list or tuple of str
    :param paths: Plugin search paths.
    :type paths: list or tuple of str
    :param ignore_errors: If a plugin fails to load, this determines whether to
        raise the exception or simply print an error and keep going.
    :type ignore_errors: bool
    :param quiet: Optionally suppress printing status messages.
    :type quiet: bool
    :return: Set of plugins that were loaded successfully.
    :rtype: set
    """
    loaded = set()
    for plugin in plugins:
        try:
            load_plugin(plugin, paths)
            loaded.add(plugin)
            if not quiet:
                print(TerminalColor.success('Loaded plugin "%s"' % plugin))
        except Exception:
            print(TerminalColor.error(
                'ERROR: Failed to load plugin "%s":' % plugin))
            if ignore_errors:
                traceback.print_exc()
            else:
                raise

    return loaded


def load_plugin(name, paths):
    """
    Enable a plugin for the romanesco runtime.

    :param name: The name of the plugin to load, which is also the name of its
        containing directory.
    :type name: str
    :param paths: Plugin search paths.
    :type paths: list or tuple of str
    """
    if 'romanesco.plugins' not in sys.modules:
        module = imp.new_module('romanesco.plugins')
        romanesco.plugins = module
        sys.modules['romanesco.plugins'] = module

    for path in paths:
        plugin_dir = os.path.join(path, name)
        if os.path.isdir(plugin_dir):
            moduleName = 'romanesco.plugins.' + name

            if moduleName not in sys.modules:
                fp, pathname, description = imp.find_module(name, [path])
                module = imp.load_module(moduleName, fp, pathname, description)
                setattr(romanesco.plugins, name, module)

                if hasattr(module, 'load'):
                    module.load({
                        'plugin_dir': plugin_dir
                    })
            break
    else:
        raise PluginNotFoundException(
            'Plugin "%s" not found. Looked in: \n   %s\n' % (
                name, '\n   '.join(paths)))


def run_process(command, outputs, print_stdout, print_stderr):
    p = subprocess.Popen(args=command, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    fds = [p.stdout, p.stderr]
    while True:
        ready = select.select(fds, (), fds, 1)[0]

        if p.stdout in ready:
            buf = os.read(p.stdout.fileno(), 1024)
            if buf:
                if print_stdout:
                    sys.stdout.write(buf)
                else:
                    outputs['_stdout']['script_data'] += buf
            else:
                fds.remove(p.stdout)
        if p.stderr in ready:
            buf = os.read(p.stderr.fileno(), 1024)
            if buf:
                if print_stderr:
                    sys.stderr.write(buf)
                else:
                    outputs['_stderr']['script_data'] += buf
            else:
                fds.remove(p.stderr)
        if (not fds or not ready) and p.poll() is not None:
            break
        elif not fds and p.poll() is None:
            p.wait()

    return p
