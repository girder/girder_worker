"""This module defines a data type based on a xray DataSet."""

from xray import Dataset as _Dataset

from gaia.core.data import GeospatialData


class XrayDataset(GeospatialData, _Dataset):

    """A Gaia data type based on an xray Dataset."""

    pass


__all__ = ('XrayDataset',)
