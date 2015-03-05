"""This module defines an abstract data interface used by all tasks."""

from six import add_metaclass

from .base import GaiaObject
from .factory import create_registry


DataTypeRegistry = create_registry()


@add_metaclass(DataTypeRegistry)
class Data(GaiaObject):

    """Base data type used by Gaia."""

    pass


class GeospatialData(Data):

    """Base type for all geospatial data."""

    pass


registry = DataTypeRegistry.registry()
__all__ = ('registry',)
