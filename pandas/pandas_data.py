"""This module defines a data type based on a pandas DataFrame."""

from pandas import DataFrame as _DataFrame

from gaia.core.data import registry as data_registry


class PandasDataFrame(data_registry['Data'], _DataFrame):

    """A Gaia data type based on a pandas DataFrame."""

    pass


__all__ = ('PandasDataFrame',)
