"""This module defines messages passed between tasks in a pipeline."""

import json

from .base import GaiaObject
from .factory import create_registry


MessageRegistry = create_registry()


class Message(GaiaObject, dict):

    """Define an inter-type message specification.

    A message is an arbitrary "dict"-like object used to pass information
    from one task to another.  Subclasses of this class will be added to the
    message registry to provide standard communication models.  For example,
    a slicing message type can be created to tell a file reader that only
    a subset of the full data is needed.  The slice message can be handled
    tasks individually to optimize the pipeline globally.
    """

    __metaclass__ = MessageRegistry


class JSONMessage(Message):

    """Define a JSON serializable message.

    This class is the preferred mode of communication between tasks as
    the message can be stored and passed between processes.
    """

    def __str__(self):
        """Serialize the message into JSON."""
        return json.dumps(self, default=str)


registry = MessageRegistry.registry()

__all__ = ('registry',)
