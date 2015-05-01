"""Test cases for the core stream class."""

from base import TestCase
from gaia.core import stream, Task

Stream = stream.registry['Stream']


class ZeroStream(Stream):

    """A dumb streaming class that always returns 0."""

    def read(self):
        """Return 0."""
        return 0


class Task1(Task):

    """A task with an output port."""

    output_ports = {
        'output': Task.make_output_port(ZeroStream)
    }


class Task2(Task):

    """A task with an input port."""

    input_ports = {
        'input': Task.make_input_port(ZeroStream)
    }


class TestStream(Stream):

    """A testing streaming class that tracks calls."""

    def __init__(self, obj, *arg, **kw):
        """Initialize the streamer."""
        task1 = Task1()
        task2 = Task2()

        self.obj = obj
        self.obj['nclose'] = 0
        self.obj['nflush'] = 0

        super(TestStream, self).__init__(
            task1.outputs['output'],
            task2.inputs['input']
        )

        task2.set_input(
            input=task1.get_output('output')
        )

    def flush(self):
        """Flush the stream."""
        self.obj['nflush'] += 1
        super(TestStream, self).flush()

    def close(self):
        """Close the stream."""
        self.obj['nclose'] += 1
        super(TestStream, self).close()


class TestStreamCase(TestCase):

    """Test the base stream class."""

    def test_stream_registry(self):
        """Test the stream registry."""
        self.assertEquals(
            stream.registry.get('ZeroStream'),
            ZeroStream
        )

    def test_default_stream(self):
        """Test the default streaming behavior."""
        s = TestStream({})
        d = {}
        self.assertTrue(
            s.write(d)
        )

        self.assertTrue(
            s.read() is d
        )

        self.assertTrue(
            s.read() is None
        )

    def test_close_stream(self):
        """Test flush called when closing a stream."""
        s = TestStream({})

        s.close()

        self.assertEquals(
            s.obj['nflush'],
            1
        )
        self.assertEquals(
            s.obj['nclose'],
            1
        )

    def test_delete_stream(self):
        """Test flush called when deleting a stream."""
        o = {}
        s = TestStream(o)

        del s

        self.assertEqual(o['nflush'], 1)

        TestStream(o)
        self.assertEqual(o['nflush'], 1)
