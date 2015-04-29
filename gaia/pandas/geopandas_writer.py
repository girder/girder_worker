"""This module defines a file writer based on the geopandas."""

# I think fiona is always installed with geopandas, but just in case...
try:
    from fiona import supported_drivers
except ImportError:  # pragma: nocover
    supported_drivers = []
from geopandas import GeoDataFrame

from gaia.core import Task


class GeopandasWriter(Task):

    """A task that writes geospatial files from geopandas data frames.

    Supported data formats are provided as a class attribute:
    >>> 'GeoJSON' in GeopandasWriter.formats
    True

    File name and format stored as instance properties:
    >>> writer = GeopandasWriter()
    >>> writer.file_name = 'my-file.json'
    >>> writer.format = 'not a format'
    Traceback (most recent call last):
        ...
    ValueError: Unsupported file format.
    >>> writer.format = 'GeoJSON'

    Connect to a pipeline to execute:
    >>> writer.set_input(port=reader.get_output())  # doctest: +SKIP
    >>> writer.run()                                # doctest: +SKIP
    """

    input_ports = {
        '': Task.make_input_port(GeoDataFrame)
    }

    formats = [f for f in supported_drivers if 'w' in supported_drivers[f]]

    def run(self, *args, **kw):
        """Write file data using geopandas."""
        super(GeopandasWriter, self).run(*args, **kw)
        data = self._input_data['']
        data.to_file(self.file_name, self.format)
        self.dirty = False


def _validate_format(format_type):
    """Check if the given format is supported.

    :param str format_type: A driver from fiona
    :raises ValueError: if format is unsupported

    >>> _validate_format('GeoJSON')
    True

    The format name is case sensitive:
    >>> _validate_format('geojson')
    Traceback (most recent call last):
        ...
    ValueError: Unsupported file format.
    """
    if format_type not in GeopandasWriter.formats:
        raise ValueError('Unsupported file format.')

    return True


GeopandasWriter.add_property(
    'file_name',
    on_change=GeopandasWriter._reset,
    default='file.geojson'
)

GeopandasWriter.add_property(
    'format',
    on_change=GeopandasWriter._reset,
    validator=_validate_format,
    default='GeoJSON'
)
