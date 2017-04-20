import contextlib
import errno
import functools
import imp
import json
import os
import girder_worker
import girder_worker.plugins
import select
import shutil
import six
import subprocess
import stat
import sys
import tempfile
import traceback


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
        return ''.join((tag, text, TerminalColor.ENDC))

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
    root = os.path.abspath(girder_worker.config.get(
        'girder_worker', 'tmp_root'))
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
    special kwarg "_tempdir".
    """
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        if '_tempdir' in kwargs:
            return fn(*args, **kwargs)

        cleanup = kwargs.get('cleanup', True)
        with tmpdir(cleanup=cleanup) as tempdir:
            kwargs['_tempdir'] = tempdir
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
    Enable a plugin for the worker runtime.

    :param name: The name of the plugin to load, which is also the name of its
        containing directory.
    :type name: str
    :param paths: Plugin search paths.
    :type paths: list or tuple of str
    """
    for path in paths:
        plugin_dir = os.path.join(path, name)
        if os.path.isdir(plugin_dir):
            module_name = 'girder_worker.plugins.' + name

            if module_name not in sys.modules:
                fp, pathname, description = imp.find_module(name, [path])
                module = imp.load_module(module_name, fp, pathname, description)
                setattr(girder_worker.plugins, name, module)
            else:
                module = sys.modules[module_name]

            if hasattr(module, 'load'):
                module.load({
                    'plugin_dir': plugin_dir,
                    'name': name
                })

            break
    else:
        raise PluginNotFoundException(
            'Plugin "%s" not found. Looked in: \n   %s\n' % (
                name, '\n   '.join(paths)))


def _close_pipes(rds, wds, input_pipes, output_pipes, close_output_pipe):
    """
    Helper to close remaining input and output adapters after the subprocess
    completes.
    """
    # close any remaining output adapters
    for fd in rds:
        if fd in output_pipes:
            output_pipes[fd].close()
            if close_output_pipe(fd):
                os.close(fd)

    # close any remaining input adapters
    for fd in wds:
        if fd in input_pipes:
            os.close(fd)


def _setup_input_pipes(input_pipes):
    """
    Given a mapping of input pipes, return a tuple with 2 elements. The first is
    a list of file descriptors to pass to ``select`` as writeable descriptors.
    The second is a dictionary mapping paths to existing named pipes to their
    adapters.
    """
    wds = []
    fifos = {}
    for pipe, adapter in six.viewitems(input_pipes):
        if isinstance(pipe, int):
            # This is assumed to be an open system-level file descriptor
            wds.append(pipe)
        else:
            if not os.path.exists(pipe):
                raise Exception('Input pipe does not exist: %s' % pipe)
            if not stat.S_ISFIFO(os.stat(pipe).st_mode):
                raise Exception('Input pipe must be a fifo object: %s' % pipe)
            fifos[pipe] = adapter

    return wds, fifos


def _open_ipipes(wds, fifos, input_pipes):
    """
    This will attempt to open the named pipes in the set of ``fifos`` for
    writing, which will only succeed if the subprocess has opened them for
    reading already. This modifies and returns the list of write descriptors,
    the list of waiting fifo names, and the mapping back to input adapters.
    """
    for fifo in fifos.copy():
        try:
            fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
            input_pipes[fd] = fifos.pop(fifo)
            wds.append(fd)
        except OSError as e:
            if e.errno != errno.ENXIO:
                raise e

    return wds, fifos, input_pipes


def select_loop(exit_condition=lambda: True, close_output=lambda x: True,
                outputs=None, inputs=None):
    """
    Run a select loop for a set of input and output pipes

    :param exit_condition: A function to evaluate to determine if the select
        loop should terminate if all pipes are empty.
    :type exit_condition: function
    :param close_output: A function to use to test whether a output
        should be closed when EOF is reached. Certain output pipes such as
        stdout, stderr should not be closed.
    :param outputs: This should be a dictionary mapping pipe descriptors
        to instances of ``StreamPushAdapter`` that should handle the data from
        the stream. The keys of this dictionary are open file descriptors,
        which are integers.
    :type outputs: dict
    :param inputs: This should be a dictionary mapping pipe descriptors
        to instances of ``StreamFetchAdapter`` that should handle sending
        input data in chunks. Keys in this dictionary can be either open file
        descriptors (integers) or a string representing a path to an existing
        fifo on the filesystem. This second case supports the use of named
        pipes, since they must be opened for reading before they can be opened
        for writing
    :type inputs: dict
    """

    BUF_LEN = 65536
    inputs = inputs or {}
    outputs = outputs or {}

    rds = [fd for fd in outputs.keys() if isinstance(fd, int)]
    wds, fifos = _setup_input_pipes(inputs)

    try:
        while True:
            # We evaluate this first so that we get one last iteration of
            # of the loop before breaking out of the loop.
            exit = exit_condition()

            # get ready pipes, timeout of 100 ms
            readable, writable, _ = select.select(rds, wds, (), 0.1)

            for ready_fd in readable:
                buf = os.read(ready_fd, BUF_LEN)

                if buf:
                    outputs[ready_fd].write(buf)
                else:
                    outputs[ready_fd].close()
                    # Should we close this pipe? In the case of stdout or stderr
                    # bad things happen if parent closes
                    if close_output(ready_fd):
                        os.close(ready_fd)
                    rds.remove(ready_fd)
            for ready_fd in writable:
                # TODO for now it's OK for the input reads to block since
                # input generally happens first, but we should consider how to
                # support non-blocking stream inputs in the future.
                buf = inputs[ready_fd].read(BUF_LEN)

                if buf:
                    os.write(ready_fd, buf)
                else:   # end of stream
                    wds.remove(ready_fd)
                    os.close(ready_fd)

            wds, fifos, inputs = _open_ipipes(wds, fifos, inputs)
            # all pipes empty?
            empty = (not rds or not readable) and (not wds or not writable)

            if (empty and exit):
                break

    finally:
        _close_pipes(rds, wds, inputs, outputs, close_output)


def run_process(command, output_pipes=None, input_pipes=None):
    """
    Run a subprocess, and listen for its outputs on various pipes.

    :param command: The command to run.
    :type command: list of str
    :param output_pipes: This should be a dictionary mapping pipe descriptors
        to instances of ``StreamPushAdapter`` that should handle the data from
        the stream. Normally, keys of this dictionary are open file descriptors,
        which are integers. There are two special cases where they are not,
        which are the keys ``'_stdout'`` and ``'_stderr'``. These special keys
        correspond to the stdout and stderr pipes that will be created for the
        subprocess. If these are not set in the ``output_pipes`` map, the
        default behavior is to direct them to the stdout and stderr of the
        current process.
    :type output_pipes: dict
    :param input_pipes: This should be a dictionary mapping pipe descriptors
        to instances of ``StreamFetchAdapter`` that should handle sending
        input data in chunks. Keys in this dictionary can be either open file
        descriptors (integers), the special value ``'_stdin'`` for standard
        input, or a string representing a path to an existing fifo on the
        filesystem. This third case supports the use of named pipes, since they
        must be opened for reading before they can be opened for writing
    :type input_pipes: dict
    """

    p = subprocess.Popen(args=command, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, stdin=subprocess.PIPE)

    input_pipes = input_pipes or {}
    output_pipes = output_pipes or {}

    # we now know subprocess stdout and stderr filenos, so bind the adapters
    stdout = p.stdout.fileno()
    stderr = p.stderr.fileno()
    stdin = p.stdin.fileno()
    output_pipes[stdout] = output_pipes.get(
        '_stdout', WritePipeAdapter({}, sys.stdout))
    output_pipes[stderr] = output_pipes.get(
        '_stderr', WritePipeAdapter({}, sys.stderr))

    # Special case for _stdin
    if '_stdin' in input_pipes:
        input_pipes[stdin] = input_pipes['_stdin']

    def exit_condition():
        status = p.poll()
        return status is not None

    def close_output_pipe(pipe):
        return pipe not in (stdout, stderr)

    try:
        select_loop(exit_condition=exit_condition,
                    close_output=close_output_pipe,
                    outputs=output_pipes, inputs=input_pipes)
    except Exception:
        p.kill()  # kill child process if something went wrong on our end
        raise

    return p


class StreamFetchAdapter(object):
    """
    This represents the interface that must be implemented by fetch adapters
    for IO modes that want to implement streaming input.
    """
    def __init__(self, input_spec):
        self.input_spec = input_spec

    def read(self, buf_len):
        """
        Fetch adapters must implement this method, which is responsible for
        reading up to ``self.buf_len`` bytes from the stream. For now, this is
        expected to be a blocking read, and should return an empty string to
        indicate the end of the stream.
        """
        raise NotImplemented


class MemoryFetchAdapter(StreamFetchAdapter):
    def __init__(self, input_spec, data):
        """
        Simply reads data from memory. This can be used to map traditional
        (non-streaming) inputs to pipes when using ``run_process``. This is
        roughly identical behavior to BytesIO.
        """
        super(MemoryFetchAdapter, self).__init__(input_spec)
        self._stream = six.BytesIO(data)

    def read(self, buf_len):
        return self._stream.read(buf_len)


class StreamPushAdapter(object):
    """
    This represents the interface that must be implemented by push adapters for
    IO modes that want to implement streaming output.
    """
    def __init__(self, output_spec):
        """
        Initialize the adpater based on the output spec.
        """
        self.output_spec = output_spec

    def write(self, buf):
        """
        Write a chunk of data to the output stream.
        """
        raise NotImplemented

    def close(self):
        """
        Close the output stream. Called after the last data is sent.
        """
        pass


class WritePipeAdapter(StreamPushAdapter):
    """
    Simply wraps another pipe that contains a ``write`` method. This is useful
    for wrapping ``sys.stdout`` and ``sys.stderr``, where we want to call
    ``write`` but not ``close`` on them.
    """
    def __init__(self, output_spec, pipe):
        """
        :param pipe: An object containing a ``write`` method, e.g. sys.stdout.
        """
        super(WritePipeAdapter, self).__init__(output_spec)
        self.pipe = pipe

    def write(self, buf):
        self.pipe.write(buf)


class AccumulateDictAdapter(StreamPushAdapter):
    def __init__(self, output_spec, key, dictionary=None):
        """
        Appends all data from a stream under a key inside a dict. Can be used
        to bind traditional (non-streaming) outputs to pipes when using
        ``run_process``.

        :param output_spec: The output specification.
        :type output_spec: dict
        :param key: The key to accumulate the data under.
        :type key: hashable
        :param dictionary: Dictionary to write into. If not specified, uses the
            output_spec.
        :type dictionary: dict
        """
        super(AccumulateDictAdapter, self).__init__(output_spec)

        if dictionary is None:
            dictionary = output_spec

        if key not in dictionary:
            dictionary[key] = ''

        self.dictionary = dictionary
        self.key = key

    def write(self, buf):
        self.dictionary[self.key] += buf


class JobProgressAdapter(StreamPushAdapter):
    def __init__(self, job_manager):
        """
        This reads structured JSON documents one line at a time and sends
        them as progress events via the JobManager.

        :param job_manager: The job manager to use to send the progress events.
        :type job_manager: girder_worker.utils.JobManager
        """
        super(JobProgressAdapter, self).__init__(None)

        self.job_manager = job_manager
        self._buf = b''

    def write(self, buf):
        lines = buf.split(b'\n')
        if self._buf:
            lines[0] = self._buf + lines[0]
        self._buf = lines[-1]

        for line in lines[:-1]:
            self._parse(line)

    def _parse(self, line):
        try:
            doc = json.loads(line.decode('utf8'))
        except ValueError:
            return  # TODO log?

        if not isinstance(doc, dict):
            return  # TODO log?

        self.job_manager.updateProgress(
            total=doc.get('total'), current=doc.get('current'), message=doc.get('message'))
