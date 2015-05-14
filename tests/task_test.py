"""Tests for the base Task class."""

import six

from base import TestCase
from gaia.core import Task


# Define data types used by the tests
class D1(object):

    """A datatype for testing ports."""


class D2(object):

    """A datatype for testing ports."""


class S1(D1):

    """A subclass of D1."""


class S2(D2):

    """A subclass of D2."""


class SourceTask(Task):

    """A task with no inputs to use as a source."""

    output_ports = {
        '0': Task.make_output_port(D1)
    }


class SimpleTask(Task):

    """A task that counts the number of times it has executed."""

    input_ports = {'0': Task.make_input_port(D1)}
    output_ports = {
        'O1': Task.make_output_port(D1),
        'O2': Task.make_output_port(D1)
    }

    def __init__(self, *arg, **kw):
        """Create the task."""
        super(SimpleTask, self).__init__(self, *arg, **kw)
        self.count = 0

    def run(self):
        """Increment the run counter."""
        super(SimpleTask, self).run()
        self.count += 1


def make_task(input_types, output_types):
    """Generate a task with the given inputs and outputs."""
    class T(Task):

        output_ports = {}
        for n, p in six.iteritems(output_types):
            output_ports[n] = Task.make_output_port(p)

        input_ports = {}
        for n, p in six.iteritems(input_types):
            input_ports[n] = Task.make_input_port(p)
    return T


class TestCaseTask(TestCase):

    """Main test class."""

    def test_task_port_error(self):
        """Make sure tasks raise exceptions when no input is present."""
        T = make_task({'input': D1}, {'output': D1})
        t = T()
        u = T()
        self.assertEqual(t.get_input_task(name='input'), None)
        self.assertRaises(Exception, t.run)
        self.assertRaises(ValueError, t.get_output, 'not a port')
        self.assertRaises(
            ValueError,
            t.set_input,
            notaport=u.get_output('output')
        )

    def test_output_caching(self):
        """Test that task outputs are properly cached."""
        # build a task pipeline
        s = SourceTask()

        t = SimpleTask()
        t.set_input(s.get_output())

        t1 = SimpleTask()
        t1.set_input(t.get_output('O1'))
        t2 = SimpleTask()
        t2.set_input(t.get_output('O2'))

        t11 = SimpleTask()
        t11.set_input(t1.get_output('O1'))

        t12 = SimpleTask()
        t12.set_input(t1.get_output('O2'))

        t21 = SimpleTask()
        t21.set_input(t2.get_output('O1'))

        t22 = SimpleTask()
        t22.set_input(t2.get_output('O2'))

        tasks = [t, t1, t2, t11, t12, t21, t22]

        for task in tasks:
            self.assertEqual(task.count, 0)

        t12.get_output_data('O1')
        for task in [t, t1, t12]:
            self.assertEqual(task.count, 1)

        # should only execute part of the pipeline
        for task in [t2, t11, t21, t22]:
            self.assertEqual(task.count, 0)

        # get all of the outputs
        for task in tasks:
            task.get_output_data('O1')
            task.get_output_data('O2')

        # assert the caching worked
        for task in tasks:
            self.assertEqual(task.count, 1)

        # mark t as dirty and execute
        t.dirty = True
        t11.get_output_data('O1')

        # assert execution counts
        for task in [t, t1, t11]:
            self.assertEqual(task.count, 2)

        for task in [t2, t12, t21, t22]:
            self.assertTrue(task.dirty)
