"""Define the common parent type for all classes contained in the package."""


class GaiaObject(object):

    """Defines core utility methods that all classes have in common.

    As needed, add generic class methods provided universally here.
    """

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
