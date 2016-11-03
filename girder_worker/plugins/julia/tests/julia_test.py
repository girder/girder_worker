import os
import girder_worker.tasks
import shutil
import unittest

_cwd = _tmp = None


def setUpModule():
    global _tmp
    global _cwd
    _cwd = os.getcwd()
    _tmp = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'tmp')
    if not os.path.isdir(_tmp):
        os.makedirs(_tmp)
    os.chdir(_tmp)


def tearDownModule():
    os.chdir(_cwd)
    if os.path.isdir(_tmp):
        shutil.rmtree(_tmp)


class TestJuliaMode(unittest.TestCase):
    def testJuliaMode(self):
        task = {
            'mode': 'julia',
            'script': """
message = "Hello, $foo."
square = x * x
not_b = !b
f = open(file)
lines = readlines(f)
counter = 1
for l in lines
   print("$counter. $l")
   counter += 1
end
close(f)
""",
            'inputs': [
                {
                    'id': 'foo',
                    'format': 'text',
                    'type': 'string'
                },
                {
                    'id': 'x',
                    'format': 'number',
                    'type': 'number'
                },
                {
                    'id': 'file',
                    'type': 'string',
                    'format': 'text',
                    'target': 'filepath'
                },
                {
                    'id': 'b',
                    'format': 'boolean',
                    'type': 'boolean'
                }
            ],
            'outputs': [
                {
                    'id': '_stdout',
                    'format': 'text',
                    'type': 'string'
                },
                {
                    'id': 'message',
                    'format': 'text',
                    'type': 'string'
                },
                {
                    'id': 'square',
                    'format': 'number',
                    'type': 'number'
                },
                {
                    'id': 'not_b',
                    'format': 'boolean',
                    'type': 'boolean'
                }
            ]
        }

        inputs = {
            'foo': {
                'format': 'text',
                'data': 'world'
            },
            'file': {
                'format': 'text',
                'data': """It was the best of times
It was the worst of times
"""
            },
            'x': {
                'format': 'number',
                'data': 12
            },
            'b': {
                'format': 'boolean',
                'data': True
            }
        }

        out = girder_worker.tasks.run(task, inputs=inputs)

        self.assertEqual(out, {
            '_stdout': {
                'data': """1. It was the best of times
2. It was the worst of times
""",
                'format': 'text'
            },
            'message': {
                'data': 'Hello, world.',
                'format': 'text'
            },
            'square': {
                'data': 144,
                'format': 'number'
            },
            'not_b': {
                'data': False,
                'format': 'boolean'
            }
        })
