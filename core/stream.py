"""This module defines a data stream that flows through a pipeline."""

from six import add_metaclass

from gaia.core.base import GaiaObject
from gaia.core.factory import create_registry


StreamRegistry = create_registry()


@add_metaclass(StreamRegistry)
class Stream(GaiaObject):

    """Define the interface for a data stream.

    A stream is the type of object passed through a pipeline.  It is the
    primary container for data in Gaia.  Data streams should be self
    describing in that they contain all necessary metadata for interpreting
    the data.  While this class exposes a stream-like interface, the
    actual implementations can vary from websocket stream to file objects
    or in memory numpy arrays.

    The default behavior is to take an arbitrary object on write and return
    that object on read.  The reference to the object is deleted after
    reading.
    """

    def __init__(self, source_port, sink_port):
        """Create the stream between to ports.

        :param .port.OutputPort source_port: The data source
        :param .port.InputPort sink_port: THe data sink
        """
        self._output_port = sink_port
        self._input_port = source_port
        self._output = sink_port.task
        self._input = source_port.task
        self._data = None

    def read(self, *arg, **kw):
        """Read some data from the stream.

        Subclasses can define custom parameters to control the read operation,
        but when no arguments are specified the Stream should return the
        entire stream content.

        :returns: The data from the source port.
        """
        data = self._data
        self._data = None
        return data

    def write(self, data, *arg, **kw):
        """Write some data to the stream.

        Subclasses can define custom parameters to control the write operation,
        """
        self._data = data
        return True  # return status?

    def flush(self):
        """Block until the stream buffer is empty."""
        return True

    def close(self):
        """Close the stream now."""
        self.flush()
        self._data = None
        return True

    def __del__(self):
        """Delete the stream by calling py:func:Stream.close."""
        return self.close()


registry = StreamRegistry.registry()
__all__ = ('registry', 'Stream')
