"""This module defines abstract I/O tasks."""

import os

from gaia.core.task import Task


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

    """This class defines the interface for reading files."""

    pass

FileSource.add_property(
    'file_name',
    validator=os.path.exists
)

__all__ = (
    'Source', 'Sink',
    'FileSource'
)
