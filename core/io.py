"""This module defines abstract I/O tasks."""

from gaia.core.task import Task
from gaia.core.port import Port


class Source(Task):

    """This class defines an abstract data source.

    Sources have no input ports and one or more output ports.  Typically,
    these tasks will accept some kind of configuration message that limits the
    data passed through the pipeline.  Data sources can come from files, urls,
    or even be generated on the fly.
    """

    pass


class Sink(Task):

    """This class defines an abstract data sink.

    Sinks have no output ports and one or more input ports.  Data sinks can be
    specific file writers, graphics generators, diagnostic reporters or even
    logging tasks.
    """

    pass


class FileSource(Source):

    """This class defines the interface for reading local files."""

    def file_name(self, file_name=None):
        """Get or set the file name to read."""

        if file_name is None:
            return getattr(self, '_file_name')
