"""This module defines tasks executed in the pipeline."""

import six

import romanesco

from .spec import Spec
from .port_list import PortList


class Task(Spec):

    """Defines a pipeline element.

    A task is an element of the pipeline responsible for completing an
    atomic task given one or more inputs and pushing the result to the
    next task or tasks.
    """

    def __init__(self, *args, **kw):
        """Initialize the spec and add private attributes."""
        super(Task, self).__init__(*args, **kw)
        self._input_data = {}
        self._output_data = {}
        self._dirty = True

    def __setitem__(self, key, value):
        """Extend spec setitem to call PortList for input/output properties."""
        if key in ('inputs', 'outputs'):
            value = PortList(value)
        super(Task, self).__setitem__(key, value)

    def update(self, other, **kw):
        """Extend update to call PortList for input/output properties."""
        if 'inputs' in other:
            other['inputs'] = PortList(other['inputs'])
        if 'outputs' in other:
            other['outputs'] = PortList(other['outputs'])
        super(Task, self).update(other, **kw)

    def set_input(self, *arg, **kw):
        """Bind (and cache) data to input ports.

        Positional arguments map to input ports numbered as '0', '1', etc.
        Keyword arguments set inputs by name.

        Example task:
        >>> def func(a='value', b=0, c=0):
        ...     return {'d': a + ':' + str(b + c)}
        >>> spec = {
        ...     'inputs': [
        ...         {'name': 'a', 'type': 'string', 'format': 'text'},
        ...         {'name': 'b', 'type': 'number', 'format': 'number'},
        ...         {'name': 'c', 'type': 'number', 'format': 'number'},
        ...     ],
        ...     'outputs': [
        ...         {'name': 'd', 'type': 'string', 'format': 'text'}
        ...     ],
        ...     'script': func
        ... }
        >>> t1 = Task(spec)
        >>> t2 = Task(spec)
        >>> t2.script = "d = a + ';' + str(b - c)"

        # Input set from data sources
        >>> t1.set_input(a='The sum', b=2, c=3).get_output('d')
        'The sum:5'

        # Input set from data bindings (required for non-callable ``script``)
        >>> t2.set_input(a={'data': t1.get_output('d'), 'format': 'text'},
        ...              b={'data': 4, 'format': 'number'},
        ...              c={'data': 5, 'format': 'number'}).get_output('d')
        'The sum:5;-1'
        """
        # Convert arguments into keyword arguments
        for i, a in enumerate(arg):
            kw[str(i)] = a

        for name, value in six.iteritems(kw):
            if name not in self.inputs:
                raise ValueError("Invalid port name '{0}'".format(name))

            self._input_data[name] = value

            self._dirty = True
        return self

    def get_input(self, name='0'):
        """Return the data bound to the given input port.

        :param str name: An input port name
        :rtype: object or None
        """
        return self._input_data.get(name)

    def _set_output(self, val):
        """Set the output data cache.

        :param dict val: Output port -> data mapping
        """
        self._output_data = val

    def get_output(self, name='0'):
        """Return the data bound to the given output port.

        :param str name: An input port name
        :rtype: object or None
        """
        if name not in self.outputs:
            raise ValueError("Invalid port name '{0}'".format(name))
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
        all_inputs = {}
        for port in self.inputs.keys():
            all_inputs[port] = self.get_input(name=port)
        if self.mode == 'python' and callable(self.script):
            self._set_output(self.script(**all_inputs))
        else:
            all_outputs = {}
            romanesco.run(self, all_inputs, all_outputs)
            for key in self.outputs.keys():
                all_outputs[key] = self.outputs[key].fetch(all_outputs[key])
            self._set_output(all_outputs)

        self._dirty = False

    def _reset(self, *args):
        """Set dirty state for the task."""
        self._dirty = True

    def _reset_downstream(self, _, isdirty, *args):
        """Set dirty state on all downstream tasks."""
        if isdirty and not self.dirty:
            self._reset()

    @property
    def dirty(self):
        """Return the dirty state of the task."""
        return self._dirty

    _serializer = str

# add base spec properties
Task.make_property('mode', 'The execution mode of the task', 'python')
Task.make_property('script', 'A script or function to execute', '')
Task.make_property(
    'inputs',
    'A list of inputs accepted by the task',
    PortList()
)
Task.make_property(
    'outputs',
    'A list of outputs returned by the task',
    PortList()
)


__all__ = ('Task',)
