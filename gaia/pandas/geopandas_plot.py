"""This module defines a reader based on the geopandas."""

from geopandas import GeoDataFrame

from gaia.core import Task


class GeopandasPlot(Task):

    """A task that generates images from geopandas data."""

    input_ports = {
        '0': Task.make_input_port(GeoDataFrame)
    }

    def run(self, *args, **kw):
        """Plot data using geopandas."""
        super(GeopandasPlot, self).run(*args, **kw)
        data = self.get_input_data()
        if data is not None:
            plt = data.plot()
            plt.figure.savefig(self.file_name)


GeopandasPlot.add_property(
    'file_name',
    on_change=GeopandasPlot._reset
)
