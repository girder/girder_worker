import romanesco
import unittest


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

        # Use user-specified filename
        out = romanesco.run(task, inputs=inputs)

        # We bound _stderr as a task output, so it should be in the output
        self.assertEqual(out, {
            'out.csv': {
                'data': 'a,b,c\n5,2,3\n',
                'format': 'csv'
            }
        })
