from unittest import TestCase

from girder_worker.app import app
from girder_worker.describe import MissingInputException


@app.task
@app.argument('n', app.types.Integer, help='The element to return')
def fibonacci(n):
    """Compute a fibonacci number."""
    if n <= 2:
        return 1
    return fibonacci(n - 1) + fibonacci(n - 2)


@app.task
@app.argument('val', app.types.String, help='The value to return')
def keyword_func(val='test'):
    """Return a value."""
    return val


@app.task
@app.argument('arg1', app.types.String)
@app.argument('arg2', app.types.StringChoice, choices=('a', 'b'))
@app.argument('kwarg1', app.types.StringVector)
@app.argument('kwarg2', app.types.Number, min=0, max=10)
@app.argument('kwarg3', app.types.NumberMultichoice, choices=(1, 2, 3, 4, 5))
def complex_func(arg1, arg2, kwarg1=('one',), kwarg2=4, kwarg3=(1, 2)):
    return {
        'arg1': arg1,
        'arg2': arg2,
        'kwarg1': kwarg1,
        'kwarg2': kwarg2,
        'kwarg3': kwarg3
    }


@app.argument('arg1', app.types.String)
def bare_func(arg1):
    """Bare function."""
    return arg1


class DescribeDecoratorTest(TestCase):

    def test_positional_argument(self):
        desc = fibonacci.describe()
        self.assertEqual(len(desc['inputs']), 1)
        self.assertEqual(desc['name'].split('.')[-1], 'fibonacci')
        self.assertEqual(
            desc['description'],
            'Compute a fibonacci number.'
        )

        self.assertEqual(desc['inputs'][0]['name'], 'n')
        self.assertEqual(
            desc['inputs'][0]['description'],
            'The element to return'
        )

        self.assertEqual(fibonacci.call_item_task({'n': {'data': 10}}), 55)
        with self.assertRaises(MissingInputException):
            fibonacci.call_item_task({})

    def test_keyword_argument(self):
        desc = keyword_func.describe()
        self.assertEqual(len(desc['inputs']), 1)
        self.assertEqual(desc['name'].split('.')[-1], 'keyword_func')
        self.assertEqual(
            desc['description'],
            'Return a value.'
        )

        self.assertEqual(desc['inputs'][0]['name'], 'val')
        self.assertEqual(
            desc['inputs'][0]['description'],
            'The value to return'
        )

        self.assertEqual(keyword_func.call_item_task({'val': {'data': 'foo'}}), 'foo')
        self.assertEqual(keyword_func.call_item_task({}), 'test')

    def test_multiple_arguments(self):
        desc = complex_func.describe()
        self.assertEqual(len(desc['inputs']), 5)
        self.assertEqual(desc['name'].split('.')[-1], 'complex_func')

        self.assertEqual(desc['inputs'][0]['name'], 'arg1')
        self.assertEqual(desc['inputs'][1]['name'], 'arg2')
        self.assertEqual(desc['inputs'][2]['name'], 'kwarg1')
        self.assertEqual(desc['inputs'][3]['name'], 'kwarg2')
        self.assertEqual(desc['inputs'][4]['name'], 'kwarg3')

        with self.assertRaises(MissingInputException):
            complex_func.call_item_task({})

        with self.assertRaises(MissingInputException):
            complex_func.call_item_task({
                'arg1': {'data': 'value'}
            })

        with self.assertRaises(ValueError):
            complex_func.call_item_task({
                'arg1': {'data': 'value'},
                'arg2': {'data': 'invalid'}
            })

        with self.assertRaises(TypeError):
            complex_func.call_item_task({
                'arg1': {'data': 'value'},
                'arg2': {'data': 'a'},
                'kwarg2': {'data': 'foo'}
            })

        self.assertEquals(complex_func.call_item_task({
            'arg1': {'data': 'value'},
            'arg2': {'data': 'a'}
        }), {
            'arg1': 'value',
            'arg2': 'a',
            'kwarg1': ('one',),
            'kwarg2': 4,
            'kwarg3': (1, 2)
        })

        self.assertEquals(complex_func.call_item_task({
            'arg1': {'data': 'value'},
            'arg2': {'data': 'b'},
            'kwarg1': {'data': 'one,two'},
            'kwarg2': {'data': 10},
            'kwarg3': {'data': (1, 4)}
        }), {
            'arg1': 'value',
            'arg2': 'b',
            'kwarg1': ['one', 'two'],
            'kwarg2': 10,
            'kwarg3': (1, 4)
        })

    def test_bare_function(self):
        desc = bare_func.describe()
        self.assertEqual(desc['name'], 'bare_func')
        self.assertEqual(desc['description'], 'Bare function.')
        self.assertEqual(len(desc['inputs']), 1)
        self.assertEqual(desc['inputs'][0]['type'], 'string')

        returned = bare_func.call_item_task({'arg1': {'data': 'value'}})
        self.assertEqual(returned, 'value')
