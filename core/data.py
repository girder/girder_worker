"""This module defines an abstract data interface used by all tasks."""

from six import add_metaclass

from gaia.core.base import GaiaObject
from gaia.core.factory import create_registry
from gaia.core.port import InputPort, OutputPort

DataTypeRegistry = create_registry()


@add_metaclass(DataTypeRegistry)
class Data(GaiaObject):

    """Base data type used by Gaia."""

    @classmethod
    def make_port(cls, kind, type_name, name, description):
        """Return a port class that accepts this data type as an input.

        This is a convenience method for generating data type specific port classes.

        :param type kind: The port class to subclass from
        :param basestring type_name: The class name to generate
        :param basestring name: The port name
        :param basestring description: The port description
        :returns: The new port class
        """
        d = {
            'name': name,
            'description': description
        }
        return type(type_name, (kind,), d)

    @classmethod
    def make_input_port(cls, name='', description='input', type_name=None):
        """Generate an input port that accepts this data type."""

        if type_name is None:
            type_name = cls.__name__ + 'InputPort'

        return cls.make_port(InputPort, type_name, name, description)

    @classmethod
    def make_output_port(cls, name='', description='output', type_name=None):
        """Generate an output port that emits this data type."""

        if type_name is None:
            type_name = cls.__name__ + 'OutputPort'

        return cls.make_port(OutputPort, type_name, name, description)


class GeospatialData(Data):

    """Base type for all geospatial data."""

    pass


registry = DataTypeRegistry.registry()
__all__ = ('registry',)
