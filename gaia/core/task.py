"""This module defines tasks executed in the pipeline."""

import six

from gaia.core.base import GaiaObject
from gaia.core.port import InputPort, OutputPort, Port


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
        self._output_data = {}

    @property
    def inputs(self):
        """Return the dictionary of input ports."""
        return self._inputs

    @property
    def outputs(self):
        """Return the dictionary of output ports."""
        return self._outputs

    def set_input(self, *arg, **kw):
        """Bind input ports to external output ports or source data.

        Positional arguments map to input ports numbered as '0', '1', etc.
        Keyword arguments set inputs by name.  Argument values can either
        be :py:gaia.core.Port: objects to connect to other tasks
        or any other python object to set the data directly.

        Example task:
        >>> class T(Task):
        ...     input_ports = {
        ...         '0': Task.make_input_port(str),
        ...         'a': Task.make_input_port(int),
        ...         'b': Task.make_input_port(int)
        ...     }
        ...     output_ports = {
        ...         '0': Task.make_output_port(str)
        ...     }
        ...     def run(self, *a, **k):
        ...         super(T, self).run(*a, **k)
        ...         self._output_data['0'] = self.get_input_data() + ':' + str(
        ...             self.get_input_data('a') + self.get_input_data('b')
        ...         )
        ...         self._dirty = False
        >>> t1 = T()
        >>> t2 = T()

        # Input set from data sources
        >>> t1.set_input('The sum', a=2, b=3).get_output_data('0')
        'The sum:5'

        # Input set from port objects
        >>> four = Task.create_source(4).get_output()
        >>> five = Task.create_source(5).get_output()
        >>> t2.set_input(t1.get_output('0'), a=four, b=five).get_output_data('0')
        'The sum:5:9'
        """
        # Convert arguments into keyword arguments
        for i, a in enumerate(arg):
            kw[str(i)] = a

        for name, value in six.iteritems(kw):
            if name not in self._inputs:
                raise ValueError("Invalid port name '{0}'".format(name))

            if isinstance(value, Port):
                port = value
            else:
                port = Task.create_source(value).get_output()
            port.connect(self._inputs[name])

            self._dirty = True
        return self

    def get_input(self, name='0'):
        """Return the given input port.

        :param str name: An input port name
        :rtype: :py:class:OutputPort or None
        """
        return self._inputs[name]

    def get_input_task(self, name='0'):
        """Return the task attached to the given input port.

        :param str name: An input port name
        :rtype: :py:class:Task or None
        """
        port = self.get_input(name).other
        if port is None:
            return None
        return port.task

    def get_input_data(self, name='0'):
        """Return the data from the named port.

        :param str name: An input port name
        :raises Exception: if the input port is not connected
        """
        # get the task connected to the given port
        task = self.get_input_task(name)
        if task is None:
            raise Exception("Port {} is not connected".format(name))
        # get the name of the output port on the connected task
        port_name = self.get_input(name).other.name
        return task.get_output_data(name=port_name)

    def get_output(self, name='0'):
        """Return the given output port.

        :param str name: An input port name
        :rtype: :py:class:OutputPort or None
        """
        if name not in self._outputs:
            raise ValueError("Invalid port name '{0}'".format(name))
        return self._outputs[name]

    def get_output_task(self, name='0'):
        """Return the task attached to the given output port.

        :param str name: An output port name
        :rtype: :py:class:Task or None
        """
        port = self.get_output(name).other
        if port is None:
            return None
        return port.task

    def get_output_data(self, name='0'):
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
        self.dirty = False
        for port in self.inputs:
            self.get_input_data(port)

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

            name = '0'
            description = str(data)

            def emits(self):
                """Return the type of the provided datum."""
                return type(data)

        class Source(Task):

            """Generated source task."""

            output_ports = {'0': SourceOutput}

            def get_input_data(self, name='0'):
                """Return the datum associated with this source."""
                return data

            def run(self, *arg, **kw):
                """Do nothing."""
                super(Source, self).run(*arg, **kw)
                self._output_data['0'] = data

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
