"""This module defines the PortList spec."""
import six

from .spec import SpecMixin
from .port import Port


class PortList(SpecMixin, list):
    """A list that only accepts port specs.

    This class is extended to behave like a read-only dictionary, where
    the keys are the port names.

    >>> l = PortList()
    >>> l.json()
    '[]'

    Ports can be added as instances or dictionaries

    >>> l.append(Port(name='z'))
    >>> l.append({'name': 'a', 'type': 'image', 'format': 'png'})

    Normal list methods are supported

    >>> l[1] = '{"name": "b"}'
    >>> l.insert(1, {"name": "c"})
    >>> del l[1]
    >>> str(l)
    '[{"name": "z"}, {"name": "b"}]'

    Port lists have keys and values methods like dicts

    >>> l.keys()[0]
    'z'

    Ports can be referenced by either their index in the list or by name

    >>> l[0] is l['z']
    True
    >>> 'z' in l
    True

    Ports can be modified after they are added

    >>> l[0].name = 'y'
    >>> l.json()
    '[{"name": "y"}, {"name": "b"}]'

    Several validation checks are performed

    >>> l[0].name = 'b'
    Traceback (most recent call last):
        ...
    ValueError: Duplicate keys detected
    >>> l[0].name = 'a'
    >>> l[0].format = 'png'
    Traceback (most recent call last):
        ...
    ValueError: Unknown format "python.png"
    >>> str(l)
    '[{"name": "a"}, {"name": "b"}]'
    """

    def __init__(self, value=None):
        """Create an empty list and optionally populate with an iterable."""
        SpecMixin.__init__(self)
        # list.__init__(self)
        if value is not None:
            for v in value:
                self.append(v)

    def __contains__(self, value):
        """Extend to allow dict like behavior."""
        if isinstance(value, six.string_types):
            try:
                value = self.keys().index(value)
            except ValueError:
                return False
            return True
        return list.__contains__(self, value)

    def __getitem__(self, index):
        """Extend to allow indexing by port name."""
        if isinstance(index, six.string_types):
            # find the index of the port with the given name
            index = self.keys().index(index)
        return list.__getitem__(self, index)

    def __setitem__(self, index, value):
        """Replace an item in the list if possible."""
        value = self._make_port(value)
        self._can_insert(value)
        list.__setitem__(self, index, value)

    def __delitem__(self, index):
        """Remove an item from the port list, freeing handlers."""
        self[index].remove_validation_check('PortList.name')
        list.__delitem__(self, index)

    def insert(self, index, value):
        """Add an item before the given index if possible."""
        value = self._make_port(value)
        self._can_insert(value)
        list.insert(self, index, value)

    def append(self, value):
        """Append an item if possible."""
        self.insert(len(self), value)

    def _assert_no_duplicates(self):
        """Raise a ValueError if there are duplicate port names."""
        if len(set(self.keys())) != len(self):
            raise ValueError('Duplicate keys detected')

    def _port_changed_handler(self):
        """Return a function that handles port spec changes.

        This function assures that no port names are changed resulting
        in a duplicate key.
        """
        def handler(port, key=None, oldvalue=None, newvalue=None):
            if key in ('name', None):
                self._assert_no_duplicates()
        return handler

    def _can_insert(self, port):
        """Raise a ValueError if the port cannot be inserted.

        This method also binds validation handlers to the port specs.
        """
        if port.name in self.keys():
            raise ValueError('A port named "%s" already exists' % port.name)
        port.add_validation_check('PortList.name', self._port_changed_handler())

    def check(self):
        """Check that the port list is valid."""
        self._assert_no_duplicates()
        for port in self:
            port.check()

    def _make_port(self, port):
        """Coererce the arguement into a port spec."""
        return Port(port)

    def keys(self):
        """Return a list of port names."""
        return [port.name for port in self]

    def values(self):
        """Return a list of ports."""
        return list(self)
