import unittest
from romanesco.format import converter_path, has_converter, Validator
from networkx import NetworkXNoPath


class TestFormat(unittest.TestCase):
    def setUp(self):
        self.stringTextValidator = Validator('string', 'text')

    def test_converter_path(self):
        with self.assertRaisesRegexp(Exception,
                                     'No such validator foo/bar'):
            converter_path(Validator('foo', 'bar'),
                           Validator('foo', 'baz'))

        with self.assertRaises(NetworkXNoPath):
            converter_path(self.stringTextValidator,
                           Validator('graph', 'networkx'))

        self.assertEquals(converter_path(self.stringTextValidator,
                                         self.stringTextValidator), [])

        # There is a direct path from converting between these types
        self.assertEquals(len(converter_path(self.stringTextValidator,
                                             Validator('string', 'json'))), 1)

    def test_has_converter(self):
        # There are converters from string type
        self.assertTrue(has_converter(Validator('string', None)))

        # There are no converters from string/non-existent-format
        self.assertFalse(has_converter(Validator('string', 'non-existent-format')))

        # There are converters from string/text
        self.assertTrue(has_converter(self.stringTextValidator))

        # There are no converters from string/text to number/anything
        self.assertFalse(has_converter(self.stringTextValidator,
                                       Validator('number', format=None)))

        # There is a converter from string/text -> string/json
        self.assertTrue(has_converter(self.stringTextValidator,
                                      Validator('string', 'json')))

        # There are no self loops in the conversion graph
        self.assertFalse(has_converter(self.stringTextValidator,
                                       self.stringTextValidator))

        # Converters don't go from one type to another
        self.assertFalse(has_converter(Validator('string', format=None),
                                       Validator('number', format=None)))
