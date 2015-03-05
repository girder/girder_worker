"""This module defines an abstract data interface used by all tasks."""

from .base import GaiaObject
from .factory import create_registry


DataTypeRegistry = create_registry()


class Data(GaiaObject):

    """Base data type used by Gaia."""

    __metaclass__ = DataTypeRegistry


class GeospatialData(Data):

    """Base type for all geospatial data."""

    pass


registry = DataTypeRegistry.registry()
__all__ = ('registry',)
