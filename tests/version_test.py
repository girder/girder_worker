import re

from base import TestCase
import gaia


class VersionTest(TestCase):

    """Contains tests of the package version string."""

    def test_version_present(self):
        """Make sure the version is defined."""
        self.assertIn('__version__', gaia.__dict__)

    def test_version_format(self):
        """Make sure the version is formatted correctly."""
        r = re.compile(r'^\d+\.\d+\.\d+([0-9a-zA-Z]+)?$')
        self.assertRegexpMatches(gaia.__version__, r)
