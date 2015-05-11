
from base import TestCase
from gaia.core import GaiaObject


class ASubClass(GaiaObject):

    """An empty subclass for testing."""

    pass


class TestGaiaObject(TestCase):

    """Test methods defined on the base object."""

    def test_describe(self):
        """Test the core description method."""

        self.assertEqual(
            GaiaObject().describe(),
            'GaiaObject\n'
        )
        self.assertEqual(
            GaiaObject().describe('--'),
            '--GaiaObject\n'
        )

    def test_type_name(self):
        """Test the classmethod type_string."""

        self.assertEqual(
            GaiaObject.type_string(),
            "GaiaObject"
        )

        self.assertEqual(
            ASubClass().type_string(),
            "ASubClass"
        )
