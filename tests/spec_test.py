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

        t = specs.Task(self.spec)
        self.assertEquals(set(t.keys()), {'inputs', 'outputs', 'mode', 'script'})

        self.assertEquals(t['inputs'], specs.PortList())
        self.assertEquals(t['outputs'], specs.PortList())

        t2 = TempTask(self.spec)
        self.assertEquals(t2['inputs'], self.inputs)
        self.assertEquals(t2['outputs'], self.outputs)

    def test_read_only_attributes(self):

        """Raise exception if task input/output are assigned"""

        class TempTask(specs.Task):
            __inputs__ = specs.PortList(self.inputs)
            __outputs__ = specs.PortList(self.outputs)

        t = TempTask(self.spec)

        with self.assertRaises(specs.ReadOnlyAttributeException):
            t['inputs'] = specs.PortList()

        with self.assertRaises(specs.ReadOnlyAttributeException):
            t['outputs'] = specs.PortList()

        with self.assertRaises(specs.ReadOnlyAttributeException):
            t.inputs = specs.PortList()

        with self.assertRaises(specs.ReadOnlyAttributeException):
            t.outputs = specs.PortList()


if __name__ == '__main__':
    unittest.main(verbosity=2)
