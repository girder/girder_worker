import unittest
from romanesco.format import converter_path, has_converter
from networkx import NetworkXNoPath


class TestFormat(unittest.TestCase):
    def test_converter_path(self):
        with self.assertRaisesRegexp(Exception,
                                     'No such validator foo/bar'):
            converter_path(('foo', 'bar'),
                           ('foo', 'baz'))

        with self.assertRaises(NetworkXNoPath):
            converter_path(('string', 'text'),
                           ('graph', 'networkx'))

        self.assertEquals(converter_path(('string', 'text'),
                                         ('string', 'text')), [])

        # There is a direct path from converting between these types
        self.assertEquals(len(converter_path(('string', 'text'),
                                             ('string', 'json'))), 1)

    def test_has_converter(self):
        # There are converters from string type
        self.assertTrue(has_converter('string'))

        # There are no converters from string/non-existent-format
        self.assertFalse(has_converter('string', 'non-existent-format'))

        # There are converters from string/text
        self.assertTrue(has_converter('string', 'text'))

        # There are no converters from string/text to number/anything
        self.assertFalse(has_converter('string', 'text', 'number'))

        # There is a converter from string/text -> string/json
        self.assertTrue(has_converter('string', 'text', 'string', 'json'))

        # There are no self loops in the conversion graph
        self.assertFalse(has_converter('string', 'text', 'string', 'text'))

        # Converters don't go from one type to another
        self.assertFalse(has_converter('string', out_type='number'))
