import os
import romanesco
import shutil
import unittest

_cwd = _tmp = None


def setUpModule():
    global _tmp
    global _cwd
    _cwd = os.getcwd()
    _tmp = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'tmp', 'scala')
    if not os.path.isdir(_tmp):
        os.makedirs(_tmp)
    os.chdir(_tmp)


def tearDownModule():
    os.chdir(_cwd)
    if os.path.isdir(_tmp):
        shutil.rmtree(_tmp)


class TestScalaMode(unittest.TestCase):
    def testScalaMode(self):
        task = {
            'mode': 'scala',
            'script': """
println("Hello, " + args(0) + "!")
val bufferedSource = io.Source.fromFile(args(1))
for (line <- bufferedSource.getLines) {
    val cols = line.split(",").map(_.trim)
    println(s"${cols(0)}|${cols(1)}|${cols(2)}")
}
""",
            'scala_args': ['$input{foo}', '$input{file}'],
            'inputs': [
                {
                    'id': 'foo',
                    'format': 'text',
                    'type': 'string'
                },
                {
                    'id': 'file',
                    'type': 'string',
                    'format': 'text',
                    'target': 'filepath'
                }
            ],
            'outputs': [{
                'id': '_stdout',
                'format': 'text',
                'type': 'string'
            }]
        }

        inputs = {
            'foo': {
                'format': 'text',
                'data': 'world'
            },
            'file': {
                'format': 'text',
                'data': 'a,  b, c\n1,\t2,3\n'
            }
        }

        out = romanesco.run(task, inputs=inputs)

        self.assertEqual(out, {
            '_stdout': {
                'data': 'Hello, world!\na|b|c\n1|2|3\n',
                'format': 'text'
            }
        })
