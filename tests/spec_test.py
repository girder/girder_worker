"""Tests for core spec objects."""
import unittest
from unittest import TestCase
from romanesco import specs


class TestSpec(TestCase):

    """Tests edge cases of the base spec."""

    def test_key_not_str(self):
        """Raise a TypeError for invalid keys."""
        s = specs.Spec()
        with self.assertRaises(TypeError):
            s.update({0: 'value'})

    def test_delete_required_exception(self):
        """Raise an exception during a key deletion."""
        def has_required(self, *a, **kw):
            assert 'required' in self

        s = specs.Spec(required=True)
        s.add_validation_check('required', has_required)
        s.required = False  # truthiness of the value doesn't matter

        with self.assertRaises(AssertionError):
            del s['required']


class TestPort(TestCase):

    """Tests edge cases of the port spec."""

    def test_port_fetch(self):
        """Test edge cases in Port.fetch not testing in doctests."""
        port = specs.Port(name='a', type='number', format='number')

        # matching formats
        self.assertEqual(2, port.fetch({'data': 2, 'format': 'number'}))

        # invalid data
        with self.assertRaises(specs.ValidationError):
            port.fetch({'data': '2', 'format': 'number'})

        # non-matching formats
        self.assertEqual(2, port.fetch({'data': '2', 'format': 'json'}))

        # not convertable
        port.auto_convert = False
        with self.assertRaises(Exception):
            port.fetch({'data': '2', 'format': 'json'})

    def test_port_push(self):
        """Test edge cases in Port.push not testing in doctests."""
        port = specs.Port(name='a', type='number', format='number')

        # matching formats
        self.assertEqual(2, port.push({'data': 2, 'format': 'number'})['data'])

        # invalid data
        with self.assertRaises(specs.ValidationError):
            port.push({'data': '2', 'format': 'number'})

        # non-matching formats
        self.assertEqual(2, port.push({'data': '2', 'format': 'json'})['data'])

        # not convertable
        port.auto_convert = False
        with self.assertRaises(Exception):
            port.push({'data': '2', 'format': 'json'})

    def test_port_init(self):
        """Test edge cases in Port not testing in doctests."""
        p = specs.Port(name='a')
        with self.assertRaises(ValueError):
            p.type = 'notatype'


class TestAnonymousTask(TestCase):

    """Tests edge cases of the anonymous task spec."""

    def test_set_input(self):
        """Test set_input method."""
        t = specs.AnonymousTask(inputs=[{'name': 'a'}, {'name': 'b'}])
        t.outputs.append({'name': 'z'})

        with self.assertRaises(ValueError):
            t.set_input(z=0)

    def test_task_inputs_outputs_equality(self):
        """Test input and output equality through specs, task __getitem__
        interface and task __getattr__ interface."""
        inputs = sorted([
            {'name': 'a', 'type': 'string', 'format': 'text'},
            {'name': 'b', 'type': 'number', 'format': 'number'},
            {'name': 'c', 'type': 'number', 'format': 'number'},
        ])
        outputs = sorted([
            {'name': 'd', 'type': 'string', 'format': 'text'}
        ])

        spec = {
            'inputs': inputs,
            'outputs': outputs,
            'script': "d = a + ':' + str(b + c)"}

        t = specs.AnonymousTask(spec)

        self.assertEquals(sorted(spec['inputs']), inputs)
        self.assertEqual(sorted(spec['outputs']), outputs)

        self.assertEquals(sorted(t['inputs']), inputs)
        self.assertEqual(sorted(t['outputs']), outputs)

        self.assertEquals(sorted(t.inputs), inputs)
        self.assertEquals(sorted(t.outputs), outputs)


class TestTask(TestCase):

    """Tests edge cases of the task spec."""

    def setUp(self):
        self.inputs = sorted([
            {'name': 'a', 'type': 'string', 'format': 'text'},
            {'name': 'b', 'type': 'number', 'format': 'number'},
            {'name': 'c', 'type': 'number', 'format': 'number'},
        ])
        self.outputs = sorted([
            {'name': 'd', 'type': 'string', 'format': 'text'}
        ])

        self.spec = {
            'script': "d = a + ':' + str(b + c)"
        }

    def test_class_level_set_of_inputs_outputs(self):

        """Test task input/output attributes are set from class vars"""

        class TempTask(specs.Task):
            __inputs__ = specs.PortList(self.inputs)
            __outputs__ = specs.PortList(self.outputs)

        t = specs.Task("temp", self.spec)
        self.assertEquals(set(t.keys()), {'inputs', 'outputs', 'mode', 'script'})

        self.assertEquals(t['inputs'], specs.PortList())
        self.assertEquals(t['outputs'], specs.PortList())

        t2 = TempTask("temp", self.spec)
        self.assertEquals(t2['inputs'], self.inputs)
        self.assertEquals(t2['outputs'], self.outputs)

    def test_read_only_attributes(self):

        """Raise exception if task input/output are assigned"""

        class TempTask(specs.Task):
            __inputs__ = specs.PortList(self.inputs)
            __outputs__ = specs.PortList(self.outputs)

        # Test if passed in in spec dict
        with self.assertRaises(specs.ReadOnlyAttributeException):
            spec = self.spec.copy()
            spec['inputs'] = specs.PortList()
            TempTask("temp", spec)

        with self.assertRaises(specs.ReadOnlyAttributeException):
            spec = self.spec.copy()
            spec['outputs'] = specs.PortList()
            TempTask("temp", spec)

        # Test if assigned after instatiation
        t = TempTask("temp", self.spec)

        with self.assertRaises(specs.ReadOnlyAttributeException):
            t['inputs'] = specs.PortList()

        with self.assertRaises(specs.ReadOnlyAttributeException):
            t['outputs'] = specs.PortList()

        with self.assertRaises(specs.ReadOnlyAttributeException):
            t.inputs = specs.PortList()

        with self.assertRaises(specs.ReadOnlyAttributeException):
            t.outputs = specs.PortList()


class TestWorkflow(TestCase):

    def setUp(self):
        self.add_three = {
            "inputs": [
                {
                    "name": "a",
                    "type": "number",
                    "format": "number"
                }
            ],
            "outputs": [
                {
                    "name": "b",
                    "type": "number",
                    "format": "number"
                }
            ],
            "mode": "python",
            "script": "b = a + 3"
        }

        self.add_two = {
            "inputs": [
                {
                    "name": "a",
                    "type": "number",
                    "format": "number"
                }
            ],
            "outputs": [
                {
                    "name": "b",
                    "type": "number",
                    "format": "number"
                }
            ],
            "mode": "python",
            "script": "b = a + 2"
        }

        self.add = {
            "inputs": [
                {
                    "name": "a",
                    "type": "number",
                    "format": "number",
                },
                {
                    "name": "b",
                    "type": "number",
                    "format": "number"
                }
            ],
            "outputs": [
                {
                    "name": "c",
                    "type": "number",
                    "format": "number"
                }
            ],
            "script": "c = a + b",
            "mode": "python"
        }

        self.multiply = {
            "inputs": [
                {
                    "name": "in1",
                    "type": "number",
                    "format": "number"
                },
                {
                    "name": "in2",
                    "type": "number",
                    "format": "number"
                }
            ],
            "outputs": [
                {
                    "name": "out",
                    "type": "number",
                    "format": "number"
                }
            ],
            "mode": "python",
            "script": "out = in1 * in2"
        }

        self.workflow = {
            "mode": "workflow",
            "inputs": [
                {
                    "name": "x",
                    "type": "number",
                    "format": "number",
                    "default": {"format": "number", "data": 10}
                },
                {
                    "name": "y",
                    "type": "number",
                    "format": "number"
                }
            ],
            "outputs": [
                {
                    "name": "result",
                    "type": "number",
                    "format": "number"
                }
            ],
            "steps": [
                {
                    "name": "af352b243109c4235d2549",
                    "task": self.add_three,
                },
                {
                    "name": "af352b243109c4235d25fb",
                    "task": self.add_two,
                },
                {
                    "name": "af352b243109c4235d25ec",
                    "task": self.multiply,
                }
            ],
            "connections": [
                {
                    "name": "x",
                    "input_step": "af352b243109c4235d2549",
                    "input": "a"
                },
                {
                    "name": "y",
                    "input_step": "af352b243109c4235d25fb",
                    "input": "a"
                },
                {
                    "output_step": "af352b243109c4235d2549",
                    "output": "b",
                    "input_step": "af352b243109c4235d25ec",
                    "input": "in1"
                },
                {
                    "output_step": "af352b243109c4235d25fb",
                    "output": "b",
                    "input_step": "af352b243109c4235d25ec",
                    "input": "in2"
                },
                {
                    "name": "result",
                    "output_step": "af352b243109c4235d25ec",
                    "output": "out"
                }
            ]
        }


if __name__ == '__main__':
    unittest.main(verbosity=2)
