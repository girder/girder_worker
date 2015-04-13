"""This module defines a data type based on a pandas DataFrame."""

from pandas import DataFrame as _DataFrame

from gaia.core.data import Data


class PandasDataFrame(Data, _DataFrame):

    """A Gaia data type based on a pandas DataFrame."""

    pass


__all__ = ('PandasDataFrame',)
