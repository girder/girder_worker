"""Module defining python testing infrastructure."""

import os
import shutil
import sys
import tempfile
from unittest import TestCase as _TestCase

try:
    import gaia as _gaia
except Exception:
    sys.path.append(os.path.abspath(os.path.join('..', '..')))
    import gaia as _gaia

_modpath = os.path.dirname(os.path.abspath(__file__))


class TestCase(_TestCase):

    """Base testing class extending unittest.TestCase."""

    # provide gaia import as a class variable to take care of import issues
    gaia = _gaia
    outpath = os.environ.get('CTEST_BINARY_DIRECTORY')
    modpath = _modpath

    def setUp(self):  # noqa
        """Create output directory if necessary."""
        self.deleteoutputdir = False
        if self.outpath is None:
            self.outpath = tempfile.mkdtemp()
            self.deleteoutputdir = True

    def tearDown(self):  # noqa
        """Delete output directory if necessary."""
        if self.deleteoutputdir:
            try:
                shutil.rmtree(self.outputpath)
                self.outputpath = None
                self.deleteoutputdir = False
            except Exception:
                pass

    @staticmethod
    def data_path(filename=None):
        """Return an absolute path to a data file or directory."""
        pth = os.path.join(_modpath, 'data')
        if filename is not None:
            pth = os.path.join(pth, filename)
        return pth

    def output_path(self, filename=None):
        """Return an absolute path to a place to store outputs."""
        pth = self.outpath
        if filename is not None:
            pth = os.path.join(pth, filename)
        return pth
