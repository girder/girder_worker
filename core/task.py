"""This module defines tasks executed in the pipeline."""

from gaia.core.base import GaiaObject
from gaia.core.port import OutputPort


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
        for port in self.input_ports:
            itask = self.get_input_task(port.name)
            iport = self.get_input(port.name)
            if itask is None:
                raise Exception("Input port '{0}' not connected.".format(port.name))
            self._input_data[port.name] = itask.get_output_data(iport.name)

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

            output_ports = [SourceOutput]

            def __init__(self, *arg, **kw):
                """Initialize a source task."""
                super(Source, self).__init__(*arg, **kw)
                self._output_data[''] = data

            def run(self, *arg, **kw):
                """Do nothing."""
                self.dirty = False

        return Source()


Task.add_property(
    'dirty',
    doc='Stores the current cache state of the Task',
    default=True,
    on_change=Task._reset_downstream
)
