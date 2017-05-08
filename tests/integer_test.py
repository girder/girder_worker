from girder_worker.tasks import run
import unittest


class TestInteger(unittest.TestCase):

    def setUp(self):
        self.analysis = {
            'name': 'add',
            'inputs': [
                {
                    'name': 'a',
                    'type': 'integer',
                    'format': 'integer',
                    'default': {
                        'format': 'json',
                        'data': '0'
                    }
                },
                {
                    'name': 'b',
                    'type': 'integer',
                    'format': 'integer'
                }
            ],
            'outputs': [{'name': 'c', 'type': 'integer', 'format': 'integer'}],
            'script': 'c = a + b',
            'mode': 'python'
        }

    def test_integer(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {'format': 'integer', 'data': 1},
                'b': {'format': 'integer', 'data': 2}
            },
            outputs={
                'c': {'format': 'integer'}
            })
        self.assertEqual(outputs['c']['format'], 'integer')
        self.assertEqual(outputs['c']['data'], 3)

    def test_json(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {'format': 'json', 'data': '1'},
                'b': {'format': 'json', 'data': '2'}
            },
            outputs={
                'c': {'format': 'json'}
            })
        self.assertEqual(outputs['c']['format'], 'json')
        self.assertEqual(outputs['c']['data'], '3')

    def test_default(self):
        outputs = run(
            self.analysis,
            inputs={
                'b': {'format': 'integer', 'data': 2}
            },
            outputs={
                'c': {'format': 'integer'}
            })
        self.assertEqual(outputs['c']['format'], 'integer')
        self.assertEqual(outputs['c']['data'], 2)

        self.assertRaisesRegexp(
            Exception, '^Required input \'b\' not provided.$',
            run, self.analysis,
            inputs={
                'a': {'format': 'integer', 'data': 2}
            },
            outputs={
                'c': {'format': 'integer'}
            })


if __name__ == '__main__':
    unittest.main()
