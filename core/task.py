"""This module defines tasks executed in the pipeline."""

import six

from gaia.core.base import GaiaObject
from gaia.core.port import InputPort, OutputPort


class Task(GaiaObject):

    """Defines a pipeline element.

    A task is an element of the pipeline responsible for completing an
    atomic task given one or more inputs and pushing the result to the
    next task or tasks.
    """

    #: Static dictonaries of I/O ports
    #:   port name -> port class
    input_ports = {}
    output_ports = {}

    def __init__(self, *arg, **kw):
        """Initialize an abstract task."""
        #: Input connection mapping
        self._inputs = {}
        for name, port in six.iteritems(self.input_ports):
            self._inputs[name] = port(self, name=name)

        #: Output connection mapping
        self._outputs = {}
        for name, port in six.iteritems(self.output_ports):
            self._outputs[name] = port(self, name=name)

        #: data cache
        self._input_data = {}
        self._output_data = {}

    @property
    def inputs(self):
        """Return the dictionary of input ports."""
        return self._inputs

    @property
    def outputs(self):
        """Return the dictionary of output ports."""
        return self._outputs

    def set_input(self, name='', port=None, **kw):
        """Connect the given input to a port on another task.

        :param str name: An input port name
        :param :py:class:OutputPort port: The output port on the other task to use
        """
        if name not in self._inputs:
            raise ValueError("Invalid port name '{0}'".format(name))

        port.connect(self._inputs[name])
        self._dirty = True
        return self

    def get_input(self, name=''):
        """Return the given input port.

        :param str name: An input port name
        :rtype: :py:class:OutputPort or None
        """
        return self._inputs[name]

    def get_input_task(self, name=''):
        """Return the task attached to the given input port.

        :param str name: An input port name
        :rtype: :py:class:Task or None
        """
        port = self.get_input(name).other
        if port is None:
            return None
        return port.task

    def _set_input_data(self, name=''):
        """Set the data for the given input port."""
        task = self.get_input_task(name)
        if task is None:
            return None
        port = self.get_input(name)
        return port.get_output()

    def get_output(self, name=''):
        """Return the given output port.

        :param str name: An input port name
        :rtype: :py:class:OutputPort or None
        """
        if name not in self._outputs:
            raise ValueError("Invalid port name '{0}'".format(name))
        return self._outputs[name]

    def get_output_task(self, name=''):
        """Return the task attached to the given output port.

        :param str name: An output port name
        :rtype: :py:class:Task or None
        """
        port = self.get_output(name).other
        if port is None:
            return None
        return port.task

    def get_output_data(self, name=''):
        """Return the data for the given port."""
        if self.dirty:
            self.run()

        return self._output_data.get(name)

    def run(self, *arg, **kw):
        """Execute the task.

        This method requires at a minimum that all input ports are connected
        to valid data sources.  Subclasses can customize the execution with
        keyword arguments.  The reference implementation only checks that
        the input ports are all connected and raises an error if they
        aren't.
        """
        for name in self.input_ports:
            iport_name = self.get_input(name).other.name
            itask = self.get_input_task(name)
            if itask is None:
                raise Exception("Input port '{0}' not connected.".format(name))
            self._input_data[name] = itask.get_output_data(iport_name)

    def _reset(self, *args):
        """Set dirty state for the task."""
        self.dirty = True

    def _reset_downstream(self, _, isdirty, *args):
        """Set dirty state on all downstream tasks."""
        if isdirty:
            for name in self.outputs:
                task = self.get_output_task(name=name)
                if task:
                    task.dirty = True

    @classmethod
    def create_source(cls, data):
        """Generate a task that supplies the given data as output.

        This class method is useful to generate source tasks quickly
        from arbitrary python objects.  For example:

        >>> data = "some arbitrary data"
        >>> source = Task.create_source(data)
        >>> source.get_output_data()
        'some arbitrary data'
        """
        class SourceOutput(OutputPort):

            """A port attached to a source task."""

            name = ''
            description = str(data)

            def emits(self):
                """Return the type of the provided datum."""
                return type(data)

        class Source(Task):

            """Generated source task."""

            output_ports = {'': SourceOutput}

            def run(self, *arg, **kw):
                """Do nothing."""
                self._output_data[''] = data
                self.dirty = False

        return Source()

    @classmethod
    def make_input_port(cls, data_class=None, data_classes=()):
        """Create an input port that accepts the given data type.

        An input port can accept one or more data types, but for compatibility
        with the ``create_output_port`` method, the default 2 argument call
        signature will generate an input port that accepts only the given
        data class.  The keyword argument ``data_classes`` can be used
        to generate a port that accepts multiple types.

        >>> Port = Task.make_input_port(int)
        >>> int in Port({}).accepts()
        True

        >>> Port = Task.make_input_port(data_classes=(int, float))
        >>> int in Port({}).accepts()
        True
        """
        if data_class is not None:
            data_classes += (data_class,)

        class ReturnedInputPort(InputPort):

            """A subclass of InputPort accepting provided types."""

            def accepts(self):
                """Return the classes accepted by the port."""
                return data_classes

        return ReturnedInputPort

    @classmethod
    def make_output_port(cls, data_class=None):
        """Create an output port that emits the given data type.

        >>> Port = Task.make_output_port(int)
        >>> int is Port({}).emits()
        True
        """
        class ReturnedOutputPort(OutputPort):

            """A subclass of InputPort accepting provided types."""

            def emits(self):
                """Return the class emitted by the port."""
                return data_class

        return ReturnedOutputPort

Task.add_property(
    'dirty',
    doc='Stores the current cache state of the Task',
    default=True,
    on_change=Task._reset_downstream
)
