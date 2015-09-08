import os
import romanesco
import shutil
import unittest


def setUpModule():
    global _tmp
    global _cwd
    _cwd = os.getcwd()
    _tmp = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'tmp', 'swift')
    if not os.path.isdir(_tmp):
        os.makedirs(_tmp)
    os.chdir(_tmp)


def tearDownModule():
    os.chdir(_cwd)
    if os.path.isdir(_tmp):
        shutil.rmtree(_tmp)


class TestSwiftMode(unittest.TestCase):
    def testSwiftMode(self):
        task = {
            'mode': 'swift',
            'script': """
type file;

app (file out) echo_app (string s)
{
   echo s stdout=filename(out);
}

string a = arg("a", "10");

file out <"out.csv">;
out = echo_app(strcat("a,b,c\\n", a, ",2,3"));
""",
            'inputs': [{
                'id': 'a',
                'format': 'json',
                'type': 'number'
            }],
            'swift_args': ['-a=$input{a}'],
            'outputs': [{
                'id': 'out.csv',
                'type': 'table',
                'format': 'csv'
            }]
        }

        inputs = {
            'a': {
                'format': 'number',
                'data': 5
            }
        }

        out = romanesco.run(task, inputs=inputs)

        self.assertEqual(out, {
            'out.csv': {
                'data': 'a,b,c\n5,2,3\n',
                'format': 'csv'
            }
        })
