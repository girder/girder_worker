"""This module defines a reader based on the geopandas."""

import os

from geopandas import read_file, GeoDataFrame

from gaia.core import Task


class GeopandasReader(Task):

    """A task that reads geospatial files using geopandas."""

    output_ports = {
        '0': Task.make_output_port(GeoDataFrame)
    }

    def _reset(self, *args):
        """Remove data cache."""
        super(GeopandasReader, self)._reset(*args)
        self._output_data['0'] = None

    def run(self, *args, **kw):
        """Read and cache file data using geopandas."""
        super(GeopandasReader, self).run(*args, **kw)
        self._output_data['0'] = read_file(self.file_name)


GeopandasReader.add_property(
    'file_name',
    on_change=GeopandasReader._reset,
    validator=os.path.exists
)
