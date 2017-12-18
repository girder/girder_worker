"""Tests for the "Pickle" data type."""
import unittest
import tempfile
import six

from girder_worker.tasks import run
from girder_worker.plugins.types import convert


class TestPickle(unittest.TestCase):
    """Tests for the "Pickle" data type."""

    def round_trip(self, obj):
        """Convert an object to base64 and back returning the new object."""
        b64 = convert(
            'python',
            {'format': 'object', 'data': obj},
            {'format': 'pickle.base64'}
        )['data']
        newobj = convert(
            'python',
            {'format': 'pickle.base64', 'data': b64},
            {'format': 'object'}
        )
        return newobj['data']

    def assertRoundTrip(self, obj, descr):
        """Assert an object is unchanged in format conversion round trip."""
        self.assertEqual(obj, self.round_trip(obj), descr)

    def test_pickle_basic(self):
        """Test pickling basic Python types."""
        self.assertRoundTrip(0, 'int')
        self.assertRoundTrip(1.0, 'float')
        self.assertRoundTrip('a', 'str')
        self.assertRoundTrip(u'\u03c0', 'unicode')
        self.assertRoundTrip('\xff\xff', 'bytes')
        self.assertRoundTrip((0, 'a'), 'tuple')
        self.assertRoundTrip([0, 'a'], 'list')
        self.assertRoundTrip({'a': 0, 'b': None}, 'dict')
        self.assertRoundTrip(
            {'a': {'c': [1, 2, {'key': ('value',)}], 'b': None}},
            'nested dict'
        )

    def test_pickle_error(self):
        """Make sure an exception is raised for non-pickleable types."""
        with self.assertRaises(Exception):
            self.round_trip(tempfile.TemporaryFile())

        with self.assertRaises(Exception):
            self.round_trip(lambda x: x)

    def run_basic_task(self, inputs):
        """Run a basic task with pickle types."""
        script = """
c = a * b
d = b + b
"""
        task = {
            'inputs': [
                {'name': 'a', 'type': 'python', 'format': 'object'},
                {'name': 'b', 'type': 'python', 'format': 'object'}
            ],
            'outputs': [
                {'name': 'c', 'type': 'python', 'format': 'object'},
                {'name': 'd', 'type': 'python', 'format': 'object'}
            ],
            'script': script,
            'mode': 'python'
        }
        d = run(task, inputs=inputs, outputs={'format': 'object'})
        for k, v in six.iteritems(d):
            if isinstance(v, dict):
                d[k] = v.get('data')
        return d

    def test_basic_task(self):
        """Run a task without conversion."""
        outputs = self.run_basic_task({
            'a': {'format': 'object', 'data': '*'},
            'b': {'format': 'object', 'data': 4}}
        )

        self.assertEqual(outputs.get('c'), '****')
        self.assertEqual(outputs.get('d'), 8)

        outputs = self.run_basic_task({
            'a': {'format': 'object', 'data': 1.0},
            'b': {'format': 'object', 'data': 4}}
        )

        self.assertEqual(outputs.get('c'), 4.0)
        self.assertEqual(outputs.get('d'), 8)

    def test_inputs_from_file(self):
        """Run a task with base64 inputs in a file."""
        a = tempfile.NamedTemporaryFile()
        b = tempfile.NamedTemporaryFile()

        convert(
            'python',
            {'format': 'object', 'data': (0, 1)},
            {'format': 'pickle.base64', 'mode': 'local', 'path': a.name}
        )

        convert(
            'python',
            {'format': 'object', 'data': 2},
            {'format': 'pickle.base64', 'mode': 'local', 'path': b.name}
        )

        outputs = self.run_basic_task({
            'a': {'format': 'pickle.base64', 'mode': 'local', 'path': a.name},
            'b': {'format': 'pickle.base64', 'mode': 'local', 'path': b.name}
        })

        self.assertEqual(outputs.get('c'), (0, 1, 0, 1))
        self.assertEqual(outputs.get('d'), 4)
