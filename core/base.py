"""Define the common parent type for all classes contained in the package."""

import six


class GaiaObject(object):

    """Defines core utility methods that all classes have in common.

    As needed, add generic class methods provided universally here.
    """

    def __init__(self, *arg, **kw):
        """Initialize instance properties."""

        for key, value in six.iteritems(kw):
            if hasattr(self.__class__, key):
                getattr(self.__class__, key).fset(self, value)

    def describe(self, tab=''):
        """Return a string representation of the instance.

        Should be overloaded by subclasses.

        :param str tab: Prepend every line added with the given string.
        :returns: Self description ending in a new line.
        :rtype: str
        """
        return tab + self.type_string() + '\n'

    @classmethod
    def type_string(cls):
        """Return a string description of a class type.

        :returns: Class name
        :rtype: str
        """
        return cls.__name__

    @classmethod
    def add_property(cls, name,
                     default=None, doc=None,
                     validator=None, on_change=None):
        """Add a new property getter/setter/deleter to the class.

        A property is stored as a private attribute on the class instances.  This
        method will create getters, setters, and deleters to the private attribute.
        This method is a helper around the standard ``@property`` python decorator.
        You can provide decorators for the standard methods to override the default
        behavior.

        :param str name: The property name
        :param str doc: The property docstring
        :param default: The default property value
        :param function validator: A method that returns True on valid input
        :param function on_change: A method to call when the value changes

        Default behavior of properties:

        >>> class MyCls(GaiaObject): pass
        >>> MyCls.add_property('foo')
        >>> c = MyCls(other='ignored')
        >>> print(c.foo)
        None
        >>> c.foo = 'bar'
        >>> print(c.foo)
        bar
        >>> print(MyCls.foo.__doc__)
        Get or set property "foo".
        >>> del c.foo
        >>> c.foo is None
        True
        >>> c = MyCls(foo='initial')
        >>> print(c.foo)
        initial

        Example of setting the docstring:

        >>> MyCls.add_property('foo', doc='property foo')
        >>> MyCls.foo.__doc__ == 'property foo'
        True

        Example of using a custom validator:

        >>> def isString(val):
        ...     return isinstance(val, six.string_types)
        >>> MyCls.add_property('foo', validator=isString, default='')
        >>> c = MyCls()
        >>> c.foo = 'a'
        >>> c.foo = 1
        Traceback (most recent call last):
            ...
        ValueError: Invalid value for property "foo"
        >>> del c.foo
        >>> c.foo == ''
        True

        Using the ``on_change`` method:

        >>> def update(self, prop, value):
        ...     print('Property "{0}" changed to "{1}"'.format(prop, value))
        >>> MyCls.add_property('foo', on_change=update)
        >>> c = MyCls(foo='initial')
        Property "foo" changed to "initial"
        >>> c.foo = 'initial'
        >>> c.foo = 'new'
        Property "foo" changed to "new"

        """

        # The private attribute name
        pvt = '_gaia_' + name

        # the getter
        def prop(self):
            return getattr(self, pvt, default)

        # the setter
        def set_prop(self, value):
            current = prop(self)
            if validator is not None:
                valid = validator(value)
                if not valid:
                    raise ValueError(
                        'Invalid value for property "{0}"'.format(name)
                    )
            setattr(self, pvt, value)
            if on_change is not None and current != value:
                on_change(self, name, value)
            return self

        def del_prop(self):
            setattr(self, pvt, default)

        if doc is None:
            doc = 'Get or set property "{0}".'.format(name)

        # add the property methods
        setattr(cls, name, property(prop, set_prop, del_prop, doc))

#        Example of using a custom decorator in the future:
#
#        >>> def debug(func):
#        ...     @wraps(func)
#        ...     def wrapped():
#        ...         val = func()
#        ...         print(val)
#        ...         return val
#        ...     return wrapped
#        ...
#        >>> class MyCls(GaiaObject): pass
#        >>> MyCls.add_property('foo', getter=debug)
#        >>> c = MyCls()
#        >>> foo = c.foo()
#        None
#        >>> c.foo('bar')
#        >>> foo = c.foo()
#        bar
