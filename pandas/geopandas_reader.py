"""This module defines a reader based on the geopandas."""

from gaia.geopandas_data import GeopandasDataFrame
from gaia.core import Task


class GeopandasReader(Task):

    """A task that reads geospatial files using geopandas."""

    output_ports = [
        GeopandasDataFrame.make_output_port()
    ]
