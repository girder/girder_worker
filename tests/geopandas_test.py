import os
import shutil
import tempfile

import matplotlib
matplotlib.use('Agg')  # noqa

from base import TestCase
from gaia.pandas import GeopandasWriter, GeopandasReader, GeopandasPlot


class GeopandasIOTest(TestCase):

    """Test the geopandas file reader and writer."""

    def setUp(self):  # noqa
        """Create a temp directory."""
        self.dir = tempfile.mkdtemp()

    def tearDown(self):  # noqa
        """Delete the temporary directory."""
        shutil.rmtree(self.dir)

    def reader(self, fname):
        """Read a file from the local data store."""
        reader = GeopandasReader()
        reader.file_name = self.data_path(fname)
        return reader

    def writer(self, reader, fname, format):
        """Write a file using geopandas writer."""
        writer = GeopandasWriter()
        writer.file_name = fname
        writer.format = format
        writer.set_input(port=reader.get_output())
        return writer

    def test_read_geojson_write_shp(self):
        """Validate the contents of a simple geojson file."""
        reader = self.reader('geopoints.json')
        data = reader.get_output_data()

        self.assertTrue('elevation' in data)
        self.assertTrue('geometry' in data)
        self.assertTrue(data.geometry[0].geom_type == 'Point')

        fname = os.path.join(self.dir, 'shapefile')
        writer = self.writer(reader, fname, 'ESRI Shapefile')
        writer.run()

        self.assertTrue(os.path.isdir(fname))
        self.assertTrue(os.path.isfile(os.path.join(fname, 'shapefile.shp')))

    def test_read_geojson_write_geojson(self):
        """Validate the contents of a simple geojson file."""
        reader = self.reader('geopoints.json')
        data = reader.get_output_data()

        self.assertTrue('elevation' in data)
        self.assertTrue('geometry' in data)
        self.assertTrue(data.geometry[0].geom_type == 'Point')

        fname = os.path.join(self.dir, 'file.json')
        writer = self.writer(reader, fname, 'GeoJSON')
        writer.run()

        self.assertTrue(os.path.isfile(fname))

        reader.file_name = fname

        data2 = reader.get_output_data()

        # the data should be reloaded in a new object
        self.assertTrue(data is not data2)
        self.assertTrue((data.elevation == data2.elevation).all())

    def test_read_shp_write_geojson(self):
        """Validate the contents of a simple geojson file."""
        reader = self.reader('shapefile')
        data = reader.get_output_data()

        self.assertTrue('elevation' in data)
        self.assertTrue('geometry' in data)
        self.assertTrue(data.geometry[0].geom_type == 'Point')

        fname = os.path.join(self.dir, 'file.json')
        writer = self.writer(reader, fname, 'GeoJSON')
        writer.run()

        self.assertTrue(os.path.isfile(fname))


class GeopandasPlotTest(TestCase):

    """Test the geopandas plotter."""

    def setUp(self):  # noqa
        """Read a small geojson file."""
        TestCase.setUp(self)
        self.reader = GeopandasReader()
        self.reader.file_name = self.data_path('geopoints.json')

    def _plot_geojson(self, ext):
        """Read a small geojson file and save a plot."""

        plotter = GeopandasPlot()
        plotter.set_input(port=self.reader.get_output())
        plotter.file_name = self.output_path('geopoints.' + ext)

        plotter.run()
        self.assertTrue(os.path.exists(plotter.file_name))

    def test_plot_geojson_png(self):
        """Create a png image."""
        self._plot_geojson('png')

    def test_plot_geojson_pdf(self):
        """Create a pdf image."""
        self._plot_geojson('pdf')
