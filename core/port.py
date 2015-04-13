"""This module defines I/O ports that serve as interfaces between tasks."""

from gaia.core.base import GaiaObject


class Port(GaiaObject):

    """A port defines a communication channel between tasks.

    Ports enable bidirectional communication between tasks and are responsible
    for ensuring that the connections are compatible.  The primary purpose of
    ports is to specify what types of data tasks can read and write.  This
    information is used by tasks to determine if they can be connected.  Ports
    also provide documentation for the task by describing its inputs and outputs.
    """

    #: The port name
    name = ''

    #: The port description
    description = ''

    def __init__(self, task):
        """Initialize the port on a given task.

        :param :py:class:task.Task task: The associated task.
        """
        self._task = task
        self._other = None

    @property
    def task(self):
        """Get the associated task."""
        return self._task

    @property
    def other(self):
        """Get the connected port or None if not connected."""
        return self._other

    def _connect(self, other):
        """Set the private other property."""
        self._other = other

    def connect(self, other):
        """Connect two ports together.

        :param other: The port on another task
        :type other: :py:class:Port
        :returns: self
        :rtype: :py:class:Port
        """
        # We can relax this if support for cyclic graphs is added
        if self.task is other.task:
            raise ValueError('Cannot connect a task to itself.')

        self._connect(other)
        other._connect(self)
        return self

    def _describe(self, kind, tab=''):
        """Return a string describing the port."""
        return "{0}{1} port '{2}': {3}\n".format(
            tab, kind, self.name, self.description
        )

    @classmethod
    def type_string(cls):
        """Return a string description of the port."""
        return '{0} {1}: {2}'.format(cls.__name__, cls.name, cls.description)


class InputPort(Port):

    """An input port accepts data flowing through the pipeline.

    As opposed to generic messages, data is only allowed to flow downstream
    in the pipeline.
    """

    def accepts(self):
        """Return the data types that this port can accept.

        :returns: a tuple of types
        :rtype: tuple
        """
        return ()

    def connect(self, other):
        """Negotiate a common format and connect two tasks together.

        Calls connect on the output port.
        """
        if not isinstance(other, OutputPort):
            raise TypeError("Invalid connection with {0}".format(other))
        return super(InputPort, self).connect(other)

    def describe(self, tab=''):
        """Return a string describing the port."""
        return self._describe('input', tab)


class OutputPort(Port):

    """An output port emits data down the pipeline.

    As opposed to generic messages, data is only allowed to flow downstream
    in the pipeline.
    """

    def compat(self, input_port):
        """Check compatibility for data passed between to classes.

        This check asserts that the data type emitted by this port is
        the same class or a subclass of the types accepted by the input
        port.

        :param input_port: Data sink
        :type input_port: :py:class:InputPort
        :returns: If connection can be made to the given input class.
        :rtype: bool
        """
        return issubclass(self.emits(), input_port.accepts())

    def emits(self):
        """Return the type that this port can emit.

        :returns: a data type subclass
        :rtype: gaia.core.data.Data
        """
        return type

    def connect(self, other):
        """Assert a common format and connect two tasks together.

        :param  other: The input port on another task to connect to.
        :type other: :py:class:InputPort
        :returns: self
        :rtype: :py:class:OutputPort
        :raises TypeError: if the ports are not compatible
        """
        if not isinstance(other, InputPort):
            raise TypeError("Invalid connection with {0}".format(other))
        if not self.compat(other):
            raise TypeError(
                "Incompatible port connection: " + str(self) +
                " -> " + str(other)
            )

        return super(OutputPort, self).connect(other)

    def describe(self, tab=''):
        """Return a string describing the port."""
        return self._describe('output', tab)
