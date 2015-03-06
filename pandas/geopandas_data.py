"""This module defines a data type based on a geopandas DataFrame."""

from geopandas import GeoDataFrame as _DataFrame

from gaia.core.data import registry as data_registry


class GeopandasDataFrame(data_registry['GeospatialData'], _DataFrame):

    """A Gaia data type based on a pandas DataFrame."""

    pass


__all__ = ('GeopandasDataFrame',)
