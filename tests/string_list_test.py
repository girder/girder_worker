from girder_worker.tasks import run
import unittest


class TestStringList(unittest.TestCase):

    def setUp(self):
        self.analysis = {
            'name': 'concatenate',
            'inputs': [
                {
                    'name': 'a',
                    'type': 'string_list',
                    'format': 'string_list',
                    'default': {
                        'format': 'json',
                        'data': '["a"]'
                    }
                },
                {
                    'name': 'b',
                    'type': 'string_list',
                    'format': 'string_list'
                }
            ],
            'outputs': [{'name': 'c',
                         'type': 'string_list', 'format': 'string_list'}],
            'script': 'c = a + b',
            'mode': 'python'
        }

    def test_string(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {'format': 'string_list', 'data': ['a', 'b']},
                'b': {'format': 'string_list', 'data': ['c', 'd']}
            },
            outputs={
                'c': {'format': 'string_list'}
            })
        self.assertEqual(outputs['c']['format'], 'string_list')
        self.assertEqual(outputs['c']['data'], ['a', 'b', 'c', 'd'])

    def test_json(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {'format': 'json', 'data': '["a", "b"]'},
                'b': {'format': 'json', 'data': '["c", "d"]'}
            },
            outputs={
                'c': {'format': 'json'}
            })
        self.assertEqual(outputs['c']['format'], 'json')
        self.assertEqual(outputs['c']['data'], '["a", "b", "c", "d"]')

    def test_default(self):
        outputs = run(
            self.analysis,
            inputs={
                'b': {'format': 'string_list', 'data': ['b']}
            },
            outputs={
                'c': {'format': 'string_list'}
            })
        self.assertEqual(outputs['c']['format'], 'string_list')
        self.assertEqual(outputs['c']['data'], ['a', 'b'])

        self.assertRaisesRegexp(
            Exception, '^Required input \'b\' not provided.$',
            run, self.analysis,
            inputs={
                'a': {'format': 'string_list', 'data': ['a']}
            },
            outputs={
                'c': {'format': 'string_list'}
            })


if __name__ == '__main__':
    unittest.main()
