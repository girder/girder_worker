"""This module defines a reader based on the geopandas."""

import os

from geopandas import read_file

from gaia.pandas.geopandas_data import GeopandasDataFrame
from gaia.core import Task


class GeopandasReader(Task):

    """A task that reads geospatial files using geopandas."""

    output_ports = [
        GeopandasDataFrame.make_output_port()
    ]

    def _reset(self, *args):
        """Remove data cache."""
        self.dirty = True
        self._output_data[''] = None

    def run(self, *args, **kw):
        """Read and cache file data using geopandas."""

        super(GeopandasReader, self).run(*args, **kw)
        if self._output_data.get('') is None:
            self._output_data[''] = read_file(self.file_name)


GeopandasReader.add_property(
    'file_name',
    on_change=GeopandasReader._reset,
    validator=os.path.exists
)
