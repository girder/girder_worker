from girder_worker.tasks import run
import unittest


class TestNumber(unittest.TestCase):

    def setUp(self):
        self.analysis = {
            'name': 'add',
            'inputs': [
                {
                    'name': 'a',
                    'type': 'number',
                    'format': 'number',
                    'default': {
                        'format': 'json',
                        'data': '0'
                    }
                },
                {
                    'name': 'b',
                    'type': 'number',
                    'format': 'number'
                }
            ],
            'outputs': [{'name': 'c', 'type': 'number', 'format': 'number'}],
            'script': 'c = a + b',
            'mode': 'python'
        }

    def test_numeric(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {'format': 'number', 'data': 1},
                'b': {'format': 'number', 'data': 2}
            },
            outputs={
                'c': {'format': 'number'}
            })
        self.assertEqual(outputs['c']['format'], 'number')
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

    def test_float(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {'format': 'number', 'data': 1.5},
                'b': {'format': 'number', 'data': 2.5}
            },
            outputs={
                'c': {'format': 'number'}
            })
        self.assertEqual(outputs['c']['format'], 'number')
        self.assertEqual(outputs['c']['data'], 4)

    def test_default(self):
        outputs = run(
            self.analysis,
            inputs={
                'b': {'format': 'number', 'data': 2}
            },
            outputs={
                'c': {'format': 'number'}
            })
        self.assertEqual(outputs['c']['format'], 'number')
        self.assertEqual(outputs['c']['data'], 2)

        self.assertRaisesRegexp(
            Exception, "^Required input 'b' not provided.$",
            run, self.analysis,
            inputs={
                'a': {'format': 'number', 'data': 2}
            },
            outputs={
                'c': {'format': 'number'}
            })


if __name__ == '__main__':
    unittest.main()
