"""Define the common parent type for all json specs contained in the package."""

import six
import json
from collections import Mapping


class Spec(dict):

    r"""
    Defines core utility methods that all spec objects have in common.

    Supports dict-like initialization.
    >>> a = Spec({'a': 1, 'b': {'c': [1, 2, None]}})
    >>> b = Spec(a=1, b={'c': [1, 2, None]})
    >>> a == b
    True

    Also supports initialization from json.
    >>> c = Spec('{"a": 1, "b": {"c": [1, 2, null]}}')
    >>> a == c
    True

    Multiple initialization method can be used together, which will be inserted
    in order.
    >>> Spec('{"a": 0}', {'a': 1}, a=2)
    {"a": 2}

    Updating merging specs is always done recursively.
    >>> Spec('{"a": {"b": 0}}', a={'c': 1})
    {"a": {"b": 0, "c": 1}}

    Conflicts are resolved by taking the value with highest priority (i.e.
    the once provided next in the constructor.)
    >>> Spec('{"a": {"b": 0}}', {"a": []})
    {"a": []}
    >>> Spec('{"a": {"b": 0}}', {"a": []}, a={"c": 1})
    {"a": {"c": 1}}
    >>> Spec('{"a": []}', {"a": {"b": 0}}, a={"c": 1})
    {"a": {"b": 0, "c": 1}}

    Serialization is performed as json
    >>> str(a)
    '{"a": 1, "b": {"c": [1, 2, null]}}'

    Strings are assumed to be utf-8 encoded.
    >>> str(Spec({u"for\u00eat": u"\ud83c\udf33 \ud83c\udf32 \ud83c\udf34"}))
    '{"for\\u00eat": "\\ud83c\\udf33 \\ud83c\\udf32 \\ud83c\\udf34"}'

    Methods that mutate the state of the Spec will test if the new state is valid,
    restoring the original state before raising an exception.
    >>> s = Spec({'a': 0})
    >>> try:
    ...     s['a'] = object
    ... except Exception:
    ...     pass
    ... else:
    ...     assert False
    >>> s
    {"a": 0}
    """

    def __init__(self, *args, **kw):
        """Initialize a new spec object.

        When called with no arguments, constructs an empty mapping.
        >>> Spec()
        {}

        Positional arguments can be mappings
        >>> Spec({})
        {}

        or JSON formatted strings.
        >>> Spec('{}')
        {}

        Multiple positional arguments are applied in order.
        >>> Spec({'a': 0}, '{"b": 1}', {'a': 2})
        {"a": 2, "b": 1}

        Items given as keyword argument will be insert last.
        >>> Spec({'a': 0}, '{"b": 1}', a=2, c=3)
        {"a": 2, "b": 1, "c": 3}
        """
        self.__initialized = False

        # empty dict initialization
        super(Spec, self).__init__()

        # process positional arguments
        for arg in args:
            if isinstance(arg, six.string_types):
                arg = json.loads(arg)
            d = dict(arg)
            self.update(d)

        # process keyword arguments
        self.update(kw)

        self.__initialized = True
        self.check()

    def update(self, other=None, **kw):
        """A recursive version of ``dict.update``."""
        if other is not None:
            _update(self, dict(other))
        _update(self, kw)

    def json(self, **kw):
        """Return the spec as a json blob.

        Keyword arguments are passed to :py:func:`json.dumps`.
        """
        return json.dumps(self, **kw)

    def __str__(self):
        """Serialize the object as json."""
        return self.json(default=str, skipkeys=True, sort_keys=True)

    def __repr__(self):
        """Serialize the object as json using repr."""
        return self.json(default=repr, skipkeys=True, sort_keys=True)

    def check(self):
        """Do internal checks ensuring the spec is valid.

        :raises ValueError: if the spec is invalid
        """
        if not self.__initialized:
            return

        try:  # let json parse it to check for errors
            self.json()
        except Exception as e:
            # reraise as a ValueError
            raise ValueError(e.message)

    def __setitem__(self, key, value):
        """Call ``dict.__setitem__`` and restore if the result is invalid."""
        restore = False
        if key in self:
            restore = True
            old = super(Spec, self).__getitem__(key)
        try:
            super(Spec, self).__setitem__(key, value)
            self.check()
        except Exception:
            if restore:
                super(Spec, self).__setitem__(key, old)
            raise

    def __delitem__(self, key):
        """Call ``dict.__delitem__`` and restore if the result is invalid."""
        restore = False
        if key in self:
            restore = True
            old = super(Spec, self).__getitem__(key)
        try:
            super(Spec, self).__delitem__(key)
            self.check()
        except Exception:
            if restore:
                super(Spec, self).__setitem__(key, old)
            raise

    @classmethod
    def make_property(cls, name, doc=None):
        """Expose a spec item as a class attribute.

        >>> class MySpec(Spec): pass
        >>> MySpec.make_property('name', doc='This is the name')
        >>> s = MySpec(name="Roger")
        >>> s.name == s['name']
        True
        >>> del s.name
        >>> 'name' in s
        False
        >>> s.name = 'Alice'
        >>> s.name == s['name']
        True
        >>> del s['name']
        >>> hasattr(s, 'name')
        False
        """
        prop = property(
            lambda self: self.__getitem__(name),
            lambda self, value: self.__setitem__(name, value),
            lambda self: self.__delitem__(name),
            doc
        )
        setattr(cls, name, prop)


def _update(d, u):
    """Update a nested dict recursively in place.

    >>> _update({'a': 0, 'b': 2}, {'a': 1})
    {'a': 1, 'b': 2}

    >>> _update({'a': {'b': 1}}, {'a': 0})
    {'a': 0}

    >>> d = _update({'a': {'b': 1}}, {'a': {'c': 2}})
    >>> d == {'a': {'b': 1, 'c': 2}}
    True
    """
    for k, v in six.iteritems(u):
        r = d.get(k, {})
        if isinstance(v, Mapping) and isinstance(r, Mapping):
            _update(r, v)
            d[k] = r
        else:
            d[k] = u[k]
    return d

__all__ = ('Spec',)
