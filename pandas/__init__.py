"""This package contains interface adapters for pandas.

On import, this package detects if pandas is installed.  If it is installed,
then the contained modules are imported to register the pandas classes with
Gaia.  If pandas is not found, this package will contain no modules.
"""


try:
    import pandas
except ImportError:
    pandas = None

__all__ = ()

if pandas is not None:
    from gaia.pandas.pandas_data import PandasDataFrame

    __all__ += ('PandasDataFrame',)

try:
    import geopandas
except ImportError:
    geopandas = None

if geopandas is not None:
    from gaia.pandas.geopandas_data import GeopandasDataFrame
    from gaia.pandas.geopandas_reader import GeopandasReader
    from gaia.pandas.geopandas_plot import GeopandasPlot

    __all__ += (
        'GeopandasDataFrame',
        'GeopandasReader',
        'GeopandasPlot'
    )

try:
    import xray
except ImportError:
    xray = None

if xray is not None:
    from gaia.pandas.xray_data import XrayDataset

    __all__ += ('XrayDataset',)
