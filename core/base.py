"""Define the common parent type for all classes contained in the package."""


class GaiaObject(object):

    """Defines core utility methods that all classes have in common.

    As needed, add generic class methods provided universally here.
    """

    _gaiaproperties = {}

    def __init__(self, *arg, **kw):
        """Initialize instance properties."""

        for key, value in self._gaiaproperties.iteritems():
            getattr(self.__class__, key).fset(self, kw.pop(key, value))

    def describe(self, tab=''):
        """Return a string representation of the instance.

        Should be overloaded by subclasses.

        :param basestring tab: Prepend every line added with the given string.
        :returns: Self description ending in a new line.
        :rtype: basestring
        """
        return tab + self.type_string() + '\n'

    @classmethod
    def type_string(cls):
        """Return a string description of a class type.

        :returns: Class name
        :rtype: basestring
        """
        return cls.__name__

    @classmethod
    def add_property(cls, name,
                     default=None, doc=None, validator=None):
        """Add a new property getter/setter/deleter to the class.

        A property is stored as a private attribute on the class instances.  This
        method will create getters, setters, and deleters to the private attribute.
        This method is a helper around the standard ``@property`` python decorator.
        You can provide decorators for the standard methods to override the default
        behavior.

        :param str name: The property name
        :param str doc: The property docstring
        :param default: The default property value
        :param function validator: A method that raises and exception on invalid input

        Default behavior of properties:

        >>> class MyCls(GaiaObject): pass
        >>> MyCls.add_property('foo')
        >>> c = MyCls()
        >>> print c.foo
        None
        >>> c.foo = 'bar'
        >>> print c.foo
        bar
        >>> print MyCls.foo.__doc__
        Get or set property "foo".
        >>> del c.foo
        >>> c.foo is None
        True


        Example of using a custom validator:

        >>> def isString(val):
        ...     if not isinstance(val, basestring):
        ...         raise TypeError('Invalid type')
        >>> class MyCls(GaiaObject): pass
        >>> MyCls.add_property('foo', validator=isString, default='')
        >>> c = MyCls()
        >>> c.foo = 'a'
        >>> c.foo = 1
        Traceback (most recent call last):
            ...
        TypeError: Invalid type
        >>> del c.foo
        >>> c.foo == ''
        True
        """

        # The private attribute name
        pvt = '_gaia_' + name

        # the getter
        def prop(self):
            return getattr(self, pvt, default)

        # the setter
        def set_prop(self, value):
            if validator is not None:
                validator(value)
            setattr(self, pvt, value)
            return self

        def del_prop(self):
            setattr(self, pvt, default)

        # register the property name
        cls._gaiaproperties[name] = default

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
