import girder_worker
import unittest


class TestR(unittest.TestCase):

    def setUp(self):
        self.array_out = {
            "inputs": [],
            "outputs": [{"name": "output", "type": "r", "format": "object"}],
            "script": "output = c(1,2,3)",
            "mode": "r"
        }

        self.array_in = {
            "inputs": [{"name": "input", "type": "r", "format": "object"}],
            "outputs": [{"name": "output", "type": "r", "format": "object"}],
            "script": "output = c(input, c(4,5))",
            "mode": "r"
        }

        self.function_out = {
            "inputs": [],
            "outputs": [{"name": "output", "type": "r", "format": "object"}],
            "script": "output = function (x) {\nreturn(x * x)\n}",
            "mode": "r"
        }

        self.function_in = {
            "inputs": [{"name": "input", "type": "r", "format": "object"}],
            "outputs": [
                {"name": "output", "type": "number", "format": "number"}],
            "script": "output = input(4)",
            "mode": "r"
        }

    def test_array(self):
        outputs = girder_worker.run(
            self.array_out,
            inputs={},
            outputs={"output": {"format": "serialized"}})
        self.assertEqual('\n'.join(outputs["output"]["data"].split('\n')[3:]),
                         "131840\n14\n3\n1\n2\n3\n")

        outputs = girder_worker.run(
            self.array_in,
            inputs={"input": outputs["output"]},
            outputs={"output": {"format": "serialized"}})
        self.assertEqual('\n'.join(outputs["output"]["data"].split('\n')[3:]),
                         "131840\n14\n5\n1\n2\n3\n4\n5\n")

    def test_function(self):
        outputs = girder_worker.run(
            self.function_out,
            inputs={},
            outputs={"output": {"format": "object"}})
        self.assertEqual(outputs["output"]["data"](3)[0], 9)
        outputs = girder_worker.run(
            self.function_in, inputs={"input": outputs["output"]})
        self.assertEqual(outputs["output"]["data"], 16)

if __name__ == '__main__':
    unittest.main()
