"""This module defines tasks executed in the pipeline."""

from .base import GaiaObject


class Task(GaiaObject):

    """Defines a pipeline element.

    A task is an element of the pipeline responsible for completing an
    atomic task given one or more inputs and pushing the result to the
    next task or tasks.
    """

    #: Static lists of I/O ports
    input_ports = []
    output_ports = []

    def __init__(self, *arg, **kw):
        """Initialize an abstract task."""

        #: Input connection mapping
        self._inputs = {}
        for p in self.input_ports:
            self._inputs[p.name] = p(self)

        #: Output connection mapping
        self._outputs = {}
        for p in self.output_ports:
            self._outputs[p.name] = p(self)

    @property
    def inputs(self):
        """Return the dictionary of input ports."""
        return self._inputs

    @property
    def outputs(self):
        """Return the dictionary of output ports."""
        return self._outputs

    def set_input(self, name, port, **kw):
        """Connect the given input to a port on another task.

        :param basestring name: An input port name
        :param :py:class:OutputPort port: The output port on the other task to use
        """

        if name not in self._inputs:
            raise ValueError("Invalid port name '{}'".format(name))

        port.connect(self._inputs[name])

    def get_input(self, name):
        """Return the output port attached to the given input port.

        :param basestring name: An input port name
        :rtype: :py:class:OutputPort or None
        """
        if name not in self._inputs:
            raise ValueError("Invalid port name '{}'".format(name))
        return self._inputs[name]

    def get_input_task(self, name):
        """Return the task attached to the given input port.

        :param basestring name: An input port name
        :rtype: :py:class:Task or None
        """
        port = self.get_input(name)
        if port is None:
            return None
        return port.other

    def get_output(self, name):
        """Return the input port connected to the given output.

        :param basestring name: An input port name
        :rtype: :py:class:OutputPort or None
        """
        if name not in self._outputs:
            raise ValueError("Invalid port name '{}'".format(name))
        return self._outputs[name]

    def get_output_task(self, name):
        """Return the task attached to the given output port.

        :param basestring name: An output port name
        :rtype: :py:class:Task or None
        """
        port = self.get_output(name)
        if port is None:
            return None
        return port.other

    def run(self, *arg, **kw):
        """Execute the task.

        This method requires at a minimum that all input ports are connected
        to valid data sources.  Subclasses can customize the execution with
        keyword arguments.  The reference implementation only checks that
        the input ports are all connected and raises an error if they
        aren't.
        """
        for port in self.input_ports:
            if self.get_input_task(port.name) is None:
                raise Exception("Input port '{}' not connected.".format(port.name))
