"""This module defines core classes that all pipeline tasks should inherit from."""

from .base import GaiaObject


class Task(GaiaObject):

    """Defines a pipeline element.

    A task is an element of the pipeline responsible for completing an
    atomic task given one or more inputs and pushing the result to the
    next task.
    """

    pass


class Source(GaiaObject):

    """Defines a pipeline data source.

    A source is connected to the first element in a pipeline.  It is responsible
    for feeding data into the pipeline.  The data can come from any source
    including a local file, remote resource, or generated on the fly.
    """

    pass
