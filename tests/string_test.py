from girder_worker.tasks import run
import unittest


class TestNumber(unittest.TestCase):

    def setUp(self):
        self.analysis = {
            'name': 'add',
            'inputs': [
                {
                    'name': 'a',
                    'type': 'string',
                    'format': 'text',
                    'default': {
                        'format': 'json',
                        'data': 'hi'
                    }
                },
                {
                    'name': 'b',
                    'type': 'string',
                    'format': 'text'
                }
            ],
            'outputs': [{'name': 'c', 'type': 'string', 'format': 'text'}],
            'script': 'c = a + b',
            'mode': 'python'
        }

    def test_text(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {'format': 'text', 'data': 'hi, '},
                'b': {'format': 'text', 'data': 'there'}
            },
            outputs={
                'c': {'format': 'text'}
            })
        self.assertEqual(outputs['c']['format'], 'text')
        self.assertEqual(outputs['c']['data'], 'hi, there')

    def test_string(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {'format': 'string', 'data': 'hi, '},
                'b': {'format': 'text', 'data': 'there'}
            },
            outputs={
                'c': {'format': 'text'}
            })
        self.assertEqual(outputs['c']['format'], 'text')
        self.assertEqual(outputs['c']['data'], 'hi, there')

    def test_json(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {'format': 'json', 'data': '"hi, "'},
                'b': {'format': 'json', 'data': '"there"'}
            },
            outputs={
                'c': {'format': 'json'}
            })
        self.assertEqual(outputs['c']['format'], 'json')
        self.assertEqual(outputs['c']['data'], '"hi, there"')

    def test_unicode(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {'format': 'text', 'data': u'hi, '},
                'b': {'format': 'text', 'data': u'there'}
            },
            outputs={
                'c': {'format': 'text'}
            })
        self.assertEqual(outputs['c']['format'], 'text')
        self.assertEqual(outputs['c']['data'], u'hi, there')
        self.assertIsInstance(outputs['c']['data'], unicode)


if __name__ == '__main__':
    unittest.main()
