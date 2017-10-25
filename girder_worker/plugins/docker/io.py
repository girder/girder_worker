import os
import errno
import stat
import abc


class StreamConnector(object):
    """
    StreamConnector is an abstract base class use to connect a read(input) and write(output)
    stream.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, input, output):
        self.input = input
        self.output = output

    @abc.abstractmethod
    def open(self):
        """
        Open the stream connector, delegated to implementation.
        """

    @abc.abstractmethod
    def close(self):
        """
        Close the stream connector, delegated to implementation.
        """

    @abc.abstractmethod
    def fileno(self):
        """
        This method allows an instance of this class to used in the select call.

        :returns The file descriptor that should be used to determine if the connector
                 has data to process.
        """
    def container_arg(self):
        """
        :returns A string that should be passed to the container as an argument in order
                 to utilize this stream. For example a named pipe path.
        """
        return ''


class WriteStreamConnector(StreamConnector):
    """
    WriteStreamConnector can be used to connect a read and write stream. The write
    side of the connection will be used in the select loop to trigger write i.e
    the file descriptor from the write stream will be used in the select call.

    This is typically used to stream data to a named pipe that will be read inside
    a container.
    """

    def fileno(self):
        """
        This method allows an instance of this class to used in the select call.

        :returns The file descriptor for write(output) side of the connection.
        """
        return self.output.fileno()

    def write(self, n=65536):
        """
        Called when it is detected the output side of this connector is ready
        to write. Reads (potentially blocks) at most n bytes and writes them to
        the output ends of this connector. If no bytes could be read, the connector
        is closed.

        :param n The maximum number of bytes to write.
        :type n int
        :returns The actual number of bytes written.
        """
        buf = self.input.read(n)

        if buf:
            return self.output.write(buf)
        else:
            self.close()

        return 0

    def open(self):
        """
        Calls open on the output side of this connector.
        """
        self.output.open()


    def close(self):
        """
        Closes the output side of this connector, followed by the input side.
        """
        self.output.close()
        if hasattr(self.input, 'close'):
            self.input.close()

    def container_arg(self):
        """
        :returns Returns any container arg associated with input side of the connector.
        """

        if hasattr(self.output, 'container_arg'):
            return self.output.container_arg()

        return ''


class ReadStreamConnector(StreamConnector):
    """
    ReadStreamConnector can be used to connect a read and write stream. The read
    side of the connection will be used in the select loop to trigger write i.e
    the file descriptor from the read stream will be used in the select call.

    This is typically used to stream data from a named pipe that is being written
    to inside a container.
    """

    def fileno(self):
        """
        This method allows an instance of this class to used in the select call.

        :returns The file descriptor for read(input) side of the connection.
        """

        return self.input.fileno()

    def read(self, n=65536):
        """
        Called when it is detected the input side of this connector is ready
        to read. Reads at most n bytes and writes them to the output ends of
        this connector. If no bytes could be read, the connector is closed.

        :param n The maximum number of bytes to read.
        :type n int
        :returns The actual number of bytes read.
        """
        buf = self.input.read(n)

        if buf:
            self.output.write(buf)
            # TODO PushAdapter/Writers should return number of bytes actually
            # written.
            return len(buf)
        else:
            self.close()

        return 0

    def open(self):
        """
        Calls open on the input side of this connector.
        """
        self.input.open()

    def close(self):
        """
        Closes the output side of this connector, followed by the input side.
        """
        self.input.close()
        self.output.close()

    def container_arg(self):
        """
        :returns A string that should be passed to the container as an argument in order
                 to utilize this stream. For example a named pipe path.
        """

        if hasattr(self.input, 'container_arg'):
            return self.input.container_arg()

        return ''


class FileDescriptorReader(object):
    def __init__(self, fd):
        self._fd = fd

    def fileno(self):
        return self._fd

    def read(self, n):
        return os.read(self.fileno(), n)

    def close(self):
        os.close(self.fileno())


class FileDescriptorWriter(object):
    def __init__(self, fd):
        self._fd = fd

    def fileno(self):
        return self._fd

    def write(self, buf):
        return os.write(self.fileno(), buf)

    def close(self):
        os.close(self.fileno())

class StdStreamReader(FileDescriptorReader):
    def close(self):
        # Bad thinks happend when you close stderr or stdout
        pass

class NamedPipe(object):
    def __init__(self, path):
        self.path = path
        self._fd = None
        os.mkfifo(self.path)

    def open(self, flags):

        if self._fd is None:
            if not os.path.exists(self.path):
                raise Exception('Input pipe does not exist: %s' % self._path)
            if not stat.S_ISFIFO(os.stat(self.path).st_mode):
                raise Exception('Input pipe must be a fifo object: %s' % self._path)

            try:
                self._fd = os.open(self.path, flags)
            except OSError as e:
                if e.errno != errno.ENXIO:
                    raise e

    def fileno(self):
        return self._fd

    def container_arg(self):
        return self.path


class NamedPipeReader(FileDescriptorReader):
    def __init__(self, pipe, container_path=None):
        super(NamedPipeReader, self).__init__(None)
        self._pipe = pipe
        self._container_path = container_path

    def open(self):
        self._pipe.open(os.O_RDONLY | os.O_NONBLOCK)

    def container_arg(self):
        return self._container_path

    def fileno(self):
        return self._pipe.fileno()


class NamedPipeWriter(FileDescriptorWriter):
    def __init__(self, pipe, container_path=None):
        super(NamedPipeWriter, self).__init__(None)
        self._pipe = pipe
        self._container_path = container_path

    def open(self):
        self._pipe.open(os.O_WRONLY | os.O_NONBLOCK)

    def container_arg(self):
        return self._container_path

    def fileno(self):
        return self._pipe.fileno()

