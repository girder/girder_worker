"""This module defines metaclass infrastructure used to build class registries."""


class MetaRegistry(type):

    """Define a metaclass that keeps a registry of derived classes.

    See http://www.cucumbertown.com/craft/python-metaclass-registry-pattern/
    """

    def __new__(cls, name, bases, attrs):
        """Create a new class derived from the given base classes."""

        new_cls = type.__new__(cls, name, bases, attrs)
        cls._registry[name] = new_cls
        return new_cls

    @classmethod
    def registry(cls):
        """Return the class registry."""

        return cls._registry


def create_registry():
    """Generate and return a new registry metaclass."""

    class NewRegistry(MetaRegistry):

        """A new registry metaclass to pass on."""

        _registry = {}

    return NewRegistry
