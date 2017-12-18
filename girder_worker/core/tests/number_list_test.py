from girder_worker.tasks import run
import unittest


class TestNumberList(unittest.TestCase):

    def setUp(self):
        self.analysis = {
            'name': 'concatenate',
            'inputs': [
                {
                    'name': 'a',
                    'type': 'number_list',
                    'format': 'number_list',
                    'default': {
                        'format': 'json',
                        'data': '[0]'
                    }
                },
                {
                    'name': 'b',
                    'type': 'number_list',
                    'format': 'number_list'
                }
            ],
            'outputs': [{'name': 'c',
                         'type': 'number_list', 'format': 'number_list'}],
            'script': 'c = a + b',
            'mode': 'python'
        }

    def test_numeric(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {'format': 'number_list', 'data': [1, 2]},
                'b': {'format': 'number_list', 'data': [3, 4]}
            },
            outputs={
                'c': {'format': 'number_list'}
            })
        self.assertEqual(outputs['c']['format'], 'number_list')
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

    def test_float(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {'format': 'number_list', 'data': [1.5, 2.5]},
                'b': {'format': 'number_list', 'data': [3.5, 4.5]}
            },
            outputs={
                'c': {'format': 'number_list'}
            })
        self.assertEqual(outputs['c']['format'], 'number_list')
        self.assertEqual(outputs['c']['data'], [1.5, 2.5, 3.5, 4.5])

    def test_default(self):
        outputs = run(
            self.analysis,
            inputs={
                'b': {'format': 'number_list', 'data': [2]}
            },
            outputs={
                'c': {'format': 'number_list'}
            })
        self.assertEqual(outputs['c']['format'], 'number_list')
        self.assertEqual(outputs['c']['data'], [0, 2])

        self.assertRaisesRegexp(
            Exception, '^Required input \'b\' not provided.$',
            run, self.analysis,
            inputs={
                'a': {'format': 'number_list', 'data': [2]}
            },
            outputs={
                'c': {'format': 'number_list'}
            })


if __name__ == '__main__':
    unittest.main()
