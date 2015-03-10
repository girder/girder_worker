"""This module defines a reader based on the geopandas."""

from gaia.pandas.geopandas_data import GeopandasDataFrame
from gaia.core import Task


class GeopandasPlot(Task):

    """A task that generates images from geopandas data."""

    input_ports = [
        GeopandasDataFrame.make_input_port()
    ]

    def _reset(self, *args):
        """Remove data cache."""
        self.dirty = True

    def run(self, *args, **kw):
        """Plot data using geopandas."""

        super(GeopandasPlot, self).run(*args, **kw)
        data = self._input_data['']
        if data is not None:
            plt = data.plot()
            plt.figure.savefig(self.file_name)
        self.dirty = False


GeopandasPlot.add_property(
    'file_name',
    on_change=GeopandasPlot._reset
)
