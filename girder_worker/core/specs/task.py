"""This module defines tasks executed in the pipeline."""

from .spec import Spec
from .port_list import PortList

from collections import MutableMapping


class ReadOnlyAttributeException(Exception):
    """Exception thrown when attempting to set a read only attribute"""
    pass


class TaskSpec(Spec):
    """Defines a pipeline element.

    A task is an element of the pipeline responsible for completing an
    atomic task given one or more inputs and pushing the result to the
    next task or tasks.
    """

    def __init__(self, *args, **kw):
        """Initialize the spec and add private attributes."""
        super(TaskSpec, self).__init__(*args, **kw)
        self._input_data = {}
        self._output_data = {}
        self._dirty = True

    def __setitem__(self, key, value):
        """Extend spec setitem to call PortList for input/output properties."""
        if key in ('inputs', 'outputs'):
            value = PortList(value)
        super(TaskSpec, self).__setitem__(key, value)

    def update(self, other, **kw):
        """Extend update to call PortList for input/output properties."""
        if 'inputs' in other:
            other['inputs'] = PortList(other['inputs'])
        if 'outputs' in other:
            other['outputs'] = PortList(other['outputs'])
        super(TaskSpec, self).update(other, **kw)

    _serializer = str


# add base spec properties
TaskSpec.make_property('mode', 'The execution mode of the task', 'python')
TaskSpec.make_property('script', 'A script or function to execute', '')
TaskSpec.make_property(
    'inputs',
    'A list of inputs accepted by the task',
    PortList()
)
TaskSpec.make_property(
    'outputs',
    'A list of outputs returned by the task',
    PortList()
)


class Task(MutableMapping):

    __inputs__ = PortList()
    __outputs__ = PortList()

    # Should probably be a property/function on Spec
    def get_spec_props(self):
        return ['mode', 'script', 'inputs', 'outputs']

    def __init__(self, spec=None, **kw):
        """Initialize the spec and add private attributes."""

        self.__spec__ = TaskSpec()

        if spec is None:
            spec = {}

        spec.update(kw)
        for k, v in spec.items():
            self[k] = v

        self.__spec__.__setitem__('inputs', self.__inputs__)
        self.__spec__.__setitem__('outputs', self.__outputs__)

    # Shadow attr getters for attributes in __spec__
    #  using Our own __getitem__ method
    def __getattr__(self, key):
        if key in self.get_spec_props():
            return self.__getitem__(key)
        else:
            return super(Task, self).__getattr__(key)

    # Shadow attr setters for attributes in __spec__
    # using our own __setitem__ method
    def __setattr__(self, key, value):
        if key in self.get_spec_props():
            return self.__setitem__(key, value)
        else:
            return super(Task, self).__setattr__(key, value)

    def __setitem__(self, key, value):
        """Extend spec setitem to call PortList for input/output properties."""

        if key in ('inputs', 'outputs'):
            raise ReadOnlyAttributeException(
                '%s is a read only attribute.' % key)
        else:
            self.__spec__.__setitem__(key, value)

    def __getitem__(self, key):
        return self.__spec__.__getitem__(key)

    def __delitem__(self, key):
        self.__spec__.__delitem__(key)

    def __iter__(self):
        return self.__spec__.__iter__()

    def __len__(self):
        return self.__spec__.__len__()

    def update(self, other=None, **kw):

        """A recursive version of ``dict.update``."""

        if other is not None:
            if {'inputs', 'outputs'} & set(other):
                raise ReadOnlyAttributeException('inputs and outputs are '
                                                 'read only attributes.')
        if {'inputs', 'outputs'} & set(kw):
            raise ReadOnlyAttributeException('inputs and outputs are '
                                             'read only attributes.')
        self.__spec__.update(other, **kw)

    def get(self, key, default=None):
        return self.__spec__.get(key, default)


__all__ = ('TaskSpec', 'Task', 'ReadOnlyAttributeException', )
