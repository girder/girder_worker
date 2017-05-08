from girder_worker.tasks import run
import unittest


class TestIntegerList(unittest.TestCase):

    def setUp(self):
        self.analysis = {
            'name': 'concatenate',
            'inputs': [
                {
                    'name': 'a',
                    'type': 'integer_list',
                    'format': 'integer_list',
                    'default': {
                        'format': 'json',
                        'data': '[0]'
                    }
                },
                {
                    'name': 'b',
                    'type': 'integer_list',
                    'format': 'integer_list'
                }
            ],
            'outputs': [{'name': 'c',
                         'type': 'integer_list', 'format': 'integer_list'}],
            'script': 'c = a + b',
            'mode': 'python'
        }

    def test_integer(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {'format': 'integer_list', 'data': [1, 2]},
                'b': {'format': 'integer_list', 'data': [3, 4]}
            },
            outputs={
                'c': {'format': 'integer_list'}
            })
        self.assertEqual(outputs['c']['format'], 'integer_list')
        self.assertEqual(outputs['c']['data'], [1, 2, 3, 4])

    def test_json(self):

        outputs = run(
            self.analysis,
            inputs={
                'a': {'format': 'json', 'data': '[1, 2]'},
                'b': {'format': 'json', 'data': '[3, 4]'}
            },
            outputs={
                'c': {'format': 'json'}
            })
        self.assertEqual(outputs['c']['format'], 'json')
        self.assertEqual(outputs['c']['data'], '[1, 2, 3, 4]')

    def test_default(self):
        outputs = run(
            self.analysis,
            inputs={
                'b': {'format': 'integer_list', 'data': [2]}
            },
            outputs={
                'c': {'format': 'integer_list'}
            })
        self.assertEqual(outputs['c']['format'], 'integer_list')
        self.assertEqual(outputs['c']['data'], [0, 2])

        self.assertRaisesRegexp(
            Exception, '^Required input \'b\' not provided.$',
            run, self.analysis,
            inputs={
                'a': {'format': 'integer_list', 'data': [2]}
            },
            outputs={
                'c': {'format': 'integer_list'}
            })


if __name__ == '__main__':
    unittest.main()
