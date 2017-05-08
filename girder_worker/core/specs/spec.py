"""Define the common parent type for all json specs contained in the package."""

import six
import json
from collections import Mapping
import copy


class SpecMixin(object):
    """An abstract mixin class implementing the Spec methods."""

    __defaults = {}

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
        # add internal validation store
        self.__checks = {}

        self.add_validation_check('Spec.json', Spec.__ensure_json)

        # process positional arguments
        for arg in args:
            if isinstance(arg, six.string_types):
                arg = json.loads(arg)
            d = dict(arg)
            self.update(d)

        # process keyword arguments
        self.update(kw)

    def __copy__(self):
        return copy.copy(dict(self))

    def __deepcopy__(self, memodict={}):
        return copy.deepcopy(dict(self))

    @staticmethod
    def _serializer(value):
        """Serialize the value or raise a TypeError."""
        return value

    def __check(self, key=None, oldvalue=None, newvalue=None, **kw):
        """Call all registered validation methods on this spec."""
        for func in six.itervalues(self.__checks):
            func(self, key, oldvalue, newvalue)

    def __ensure_json(self, key=None, oldvalue=None, newvalue=None, **kw):
        """Raise a ValueError if the spec is not valid JSON."""
        if key is None:
            for key, value in six.iteritems(self):
                self.__ensure_json(key,
                                   newvalue=value,
                                   default=self._serializer)
        elif not isinstance(key, six.string_types):
            raise TypeError('Spec keys must be string typed.')

        if newvalue is not None:
            try:
                json.dumps(newvalue, default=self._serializer)
            except Exception:
                raise ValueError(
                    '"%s" is not valid json.' % repr(newvalue)
                )

    def update(self, other=None, **kw):
        """A recursive version of ``dict.update``."""
        if other is not None:
            _update(self, dict(other))
        _update(self, kw)

    def check(self, *args, **kw):
        """Public validation of the specification.

        This works like the object mutation validation, but the call
        to the handers is made with no key.
        """
        self.__check(*args, **kw)

    def json(self, **kw):
        """Return the spec as a json blob.

        Keyword arguments are passed to :py:func:`json.dumps`.
        """
        kw.setdefault('default', self._serializer)
        self.check()
        return json.dumps(self, **kw)

    def __str__(self):
        """Serialize the object as json."""
        return self.json(default=str, skipkeys=True, sort_keys=True)

    def __repr__(self):
        """Serialize the object as json using repr."""
        return self.json(default=repr, skipkeys=True, sort_keys=True)

    def add_validation_check(self, name, func):
        """Add a method used to validate spec objects on mutation.

        :param str name: A name given to the check
        :param function func: The function to call

        Validation functions should have the following signature:

        func(self, key=None, oldvalue=None, newvalue=None, **kw)

        * self: the spec object itself
        * key: the key that changed
        * oldvalue: the old value of the key
        * newvalue: the new value of the key

        When a key is given the function can assume that all other keys in the
        spec are valid.  Old and new values of the key are given when
        applicable.  The validation function will be called whenever the spec
        is changed or on demand via the public interface :py:method:`check`.
        """
        self.__checks[name] = func

    def remove_validation_check(self, name):
        """Remove a previously added validation method."""
        self.__checks.pop(name)

    @classmethod
    def make_property(cls, name,
                      doc=None, default=None):
        """Expose a spec item as a class attribute.

        :param str name: The property name
        :param str doc: The docstring to add
        :param object default: The default value of the property
        :param function init: A constructor called on all new values

        A sample property definition
        >>> class MySpec(Spec): pass
        >>> MySpec.make_property('name', 'This is the name', 'Bob')

        Properties can be set via the Spec constructor, as an item,
        or as an attribute.  Standard attribute methods are supported.
        >>> s = MySpec(name="Roger")
        >>> s.name = 'Alice'
        >>> s.name == s['name']
        True
        >>> del s['name']
        >>> s.name
        'Bob'
        >>> s.name == s['name']
        True

        Default values are returned for unset properties
        >>> 'name' in s
        False
        >>> s['name']
        'Bob'

        Properties can be used as normal attributess

        Optionally properties can have docstrings
        >>> MySpec.name.__doc__
        'This is the name'
        """
        prop = property(
            lambda self: self.__getitem__(name),
            lambda self, value: self.__setitem__(name, value),
            lambda self: self.__delitem__(name),
            doc
        )
        cls.__defaults[name] = default
        setattr(cls, name, prop)

    def __missing__(self, key):
        """Return default for missing keys."""
        return self.__defaults.get(key, None)


class Spec(SpecMixin, dict):
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

    Methods that mutate the state of the Spec will test if the new state is
    valid, restoring the original state before raising an exception.

    >>> s = Spec({'a': 0})
    >>> try:
    ...     s['a'] = object
    ... except Exception:
    ...     pass
    ... else:
    ...     assert False
    >>> s
    {"a": 0}

    Spec constructors are idempotent

    >>> Spec(a='a') == Spec(Spec(a='a'))
    True
    """

    def __setitem__(self, key, value):
        """Call ``dict.__setitem__`` and restore if the result is invalid."""
        restore = False
        old = None
        if key in self:
            restore = True
            old = super(Spec, self).__getitem__(key)
        try:
            super(Spec, self).__setitem__(key, value)
            self.check(key=key, oldvalue=old, newvalue=value)
        except Exception:
            if restore:
                super(Spec, self).__setitem__(key, old)
            else:
                super(Spec, self).__delitem__(key)
            raise

    def __delitem__(self, key):
        """Call ``dict.__delitem__`` and restore if the result is invalid."""
        restore = False
        if key in self:
            restore = True
            old = super(Spec, self).__getitem__(key)
        try:
            super(Spec, self).__delitem__(key)
            self.check(key=key, oldvalue=old)
        except Exception:
            if restore:
                super(Spec, self).__setitem__(key, old)
            raise


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
