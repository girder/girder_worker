import romanesco
import unittest
import os


class TestSpark(unittest.TestCase):

    def setUp(self):
        self.prevdir = os.getcwd()
        cur_path = os.path.dirname(os.path.realpath(__file__))
        os.chdir(cur_path)

    def testJsonToSparkRdd(self):
        analysis = {
            'name': 'reduce',
            'inputs': [{'name': 'a', 'type': 'collection', 'format': 'spark.rdd'}],
            'outputs': [{'name': 'b', 'type': 'number', 'format': 'number'}],
            'mode': 'spark.python',
            'spark_conf': {
                'spark.app.name': 'test_add',
                'spark.master': os.environ['SPARK_TEST_MASTER_URL']
            }
        }

        with open('data/spark_add_script.py', 'r') as fp:
            script = fp.read()
            analysis['script'] = script

        outputs = romanesco.run(analysis, {
                'a': {'format': 'json', 'data': '[1,2,3,4,5,6,7,8,9]'}
            },
            {
                'b': {'format': 'number'}
            })

        expected = {'b': {'data': 45, 'format': 'number'}}
        self.assertEqual(outputs, expected)

    def testSparkRddToJson(self):
        analysis = {
            'name': 'map',
            'inputs': [{'name': 'a', 'type': 'collection', 'format': 'spark.rdd'}],
            'outputs': [{'name': 'b', 'type': 'collection', 'format': 'spark.rdd'}],
            'mode': 'spark.python',
            'spark_conf': {
                'spark.app.name': 'test_square',
                'spark.master': os.environ['SPARK_TEST_MASTER_URL']
            }
        }

        with open('data/spark_square_script.py', 'r') as fp:
            script = fp.read()
            analysis['script'] = script

        outputs = romanesco.run(analysis, {
                'a': {'format': 'json', 'data': '[1,2,3,4,5,6,7,8,9]'}
            },
            {
                'b': {'format': 'json'}
            })

        expected = {'b': {'data': '[1, 4, 9, 16, 25, 36, 49, 64, 81]', 'format': 'json'}}
        self.assertEqual(outputs, expected)

    def tearDown(self):
        os.chdir(self.prevdir)
