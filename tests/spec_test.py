"""Tests for core spec objects."""

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


class TestTask(TestCase):

    """Tests edge cases of the task spec."""

    def test_set_input(self):
        """Test set_input method."""
        t = specs.Task(inputs=[{'name': 'a'}, {'name': 'b'}])
        t.outputs.append({'name': 'z'})

        with self.assertRaises(ValueError):
            t.set_input(z=0)
