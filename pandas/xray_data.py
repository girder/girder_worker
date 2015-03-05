"""This module defines a data type based on a xray DataSet."""

from geopandas import Dataset as _Dataset

from ..core.data import registry as data_registry


class XrayDataset(data_registry['Data'], _Dataset):

    """A Gaia data type based on an xray Dataset."""

    pass


__all__ = ('XrayDataset',)
