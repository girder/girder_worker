import cardoon
import os
import tempfile
import unittest

class TestNumber(unittest.TestCase):

    def setUp(self):
        self.analysis = {
            "name": "add",
            "inputs": [{"name": "a", "type": "number", "format": "number"}, {"name": "b", "type": "number", "format": "number"}],
            "outputs": [{"name": "c", "type": "number", "format": "number"}],
            "script": "c = a + b",
            "mode": "python"
        }

    def test_numeric(self):
        outputs = cardoon.run(self.analysis,
            inputs={
                "a": {"format": "number", "data": 1},
                "b": {"format": "number", "data": 2}
            },
            outputs={
                "c": {"format": "number"}
            })
        self.assertEqual(outputs["c"]["format"], "number")
        self.assertEqual(outputs["c"]["data"], 3)

    def test_json(self):
        outputs = cardoon.run(self.analysis,
            inputs={
                "a": {"format": "json", "data": "1"},
                "b": {"format": "json", "data": "2"}
            },
            outputs={
                "c": {"format": "json"}
            })
        self.assertEqual(outputs["c"]["format"], "json")
        self.assertEqual(outputs["c"]["data"], "3")

    def test_float(self):
        outputs = cardoon.run(self.analysis,
            inputs={
                "a": {"format": "number", "data": 1.5},
                "b": {"format": "number", "data": 2.5}
            },
            outputs={
                "c": {"format": "number"}
            })
        self.assertEqual(outputs["c"]["format"], "number")
        self.assertEqual(outputs["c"]["data"], 4)

if __name__ == '__main__':
    unittest.main()
