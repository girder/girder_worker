import sys
import unittest
from girder_worker.tasks import run
from girder_worker.plugins.types.format import (
    conv_graph, converter_path, has_converter, Validator, print_conversion_graph,
    print_conversion_table)
from six import StringIO
from networkx import NetworkXNoPath


class TestFormat(unittest.TestCase):
    def setUp(self):
        self.stringTextValidator = Validator('string', 'text')

        self.prev_stdout = sys.stdout
        sys.stdout = StringIO()

    def tearDown(self):
        sys.stdout = self.prev_stdout

    def test_converter_path(self):
        with self.assertRaisesRegexp(Exception, 'No such validator foo/bar'):
            converter_path(Validator('foo', 'bar'), Validator('foo', 'baz'))

        # There is no path for types which lie in different components
        with self.assertRaises(NetworkXNoPath):
            converter_path(self.stringTextValidator,
                           Validator('graph', 'networkx'))

        self.assertEquals(converter_path(self.stringTextValidator,
                                         self.stringTextValidator), [])

        # There is a two-step path converting between these types
        self.assertEquals(len(converter_path(self.stringTextValidator,
                                             Validator('string', 'json'))), 2)

    def test_run_exceptions(self):
        number_copy = {
            'inputs': [
                {'name': 'some_number',
                 'type': 'number',
                 'format': 'number'}
            ],
            'outputs': [
                {'name': 'some_number',
                 'type': 'number',
                 'format': 'number'}
            ],
            'script': 'some_number = some_number'
        }

        # If an input has an invalid format, it should throw an exception
        # with the name
        number_copy['inputs'][0]['format'] = 'invalidformat'
        with self.assertRaisesRegexp(
                Exception,
                'some_number: No such validator number/invalidformat'):
            run(number_copy, inputs={'some_number':
                                     {'format': 'json',
                                      'data': '5'}})

        # If the input is valid, but there is no conversion path
        number_copy['inputs'][0]['format'] = 'validformat'
        conv_graph.add_node(Validator('number', 'validformat'))
        with self.assertRaisesRegexp(
                Exception,
                ('some_number: No conversion path from number/json '
                 'to number/validformat')):
            run(number_copy, inputs={'some_number':
                                     {'format': 'json',
                                      'data': '5'}})
        conv_graph.remove_node(Validator('number', 'validformat'))

    def test_is_valid(self):
        self.assertEquals(Validator('string', None).is_valid(), True)

        self.assertEquals(Validator('string', 'json').is_valid(), True)

        self.assertEquals(Validator('invalid_type', None).is_valid(), False)

        self.assertEquals(Validator('invalid_type',
                                    'invalid_format').is_valid(), False)

        self.assertEquals(Validator('string',
                                    'invalid_format').is_valid(), False)

        self.assertEquals(Validator('invalid_type',
                                    'json').is_valid(), False)

    def test_has_converter(self):
        # There are converters from string type
        self.assertTrue(has_converter(Validator('string', None)))

        # There are no converters from string/non-existent-format
        self.assertFalse(has_converter(Validator(
            'string', 'non-existent-format')))

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

        # This only has a converter which is multiple hops away
        self.assertTrue(has_converter(
            Validator('table', format='rows'),
            Validator('table', format='objectlist.json')))

    def test_conversion_graph(self):
        print_conversion_graph()

    def test_conversion_table(self):
        print_conversion_table()
