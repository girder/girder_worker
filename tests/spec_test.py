"""Tests for core spec objects."""
import unittest
import collections
from unittest import TestCase
from romanesco import specs
from romanesco.specs.utils import spec_class_generator, to_frozenset


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


class TestTaskSpec(TestCase):

    """Tests edge cases of the anonymous task spec."""

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

        t = specs.TaskSpec(spec)

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
            'script': "d = a + ':' + str(b + c)",
            'mode': "python"
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

        # Test if passed in in spec dict
        with self.assertRaises(specs.ReadOnlyAttributeException):
            spec = self.spec.copy()
            spec['inputs'] = specs.PortList()
            TempTask(spec)

        with self.assertRaises(specs.ReadOnlyAttributeException):
            spec = self.spec.copy()
            spec['outputs'] = specs.PortList()
            TempTask(spec)

        # Test if assigned after instatiation
        t = TempTask(self.spec)

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
        self.add = {
            "inputs": [{"name": "a", "type": "number", "format": "number"},
                       {"name": "b", "type": "number", "format": "number"}],
            "outputs": [{"name": "c", "type": "number", "format": "number"}],
            "script": "c = a + b",
            "mode": "python"}

        self.add_three = {
            "inputs": [{"name": "a", "type": "number", "format": "number"}],
            "outputs": [{"name": "b", "type": "number", "format": "number"}],
            "mode": "python",
            "script": "b = a + 3"}

        self.add_two = {
            "inputs": [{"name": "a", "type": "number", "format": "number"}],
            "outputs": [{"name": "b", "type": "number", "format": "number"}],
            "mode": "python",
            "script": "b = a + 2"}

        self.multiply = {
            "inputs": [{"name": "in1", "type": "number", "format": "number"},
                       {"name": "in2", "type": "number", "format": "number"}],
            "outputs": [{"name": "out", "type": "number", "format": "number"}],
            "mode": "python",
            "script": "out = in1 * in2"}

        self.workflow = {
            "mode": "workflow",

            "inputs": [{"name": "x", "type": "number", "format": "number",
                        "default": {"format": "number", "data": 10}},
                       {"name": "y", "type": "number", "format": "number"}],

            "outputs": [{"name": "result", "type": "number", "format": "number"}],

            "steps": [{"task": self.add_three, "name": "af352b243109c4235d2549"},
                      {"task": self.add_two, "name": "af352b243109c4235d25fb"},
                      {"task": self.multiply, "name": "af352b243109c4235d25ec"}],

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

    def test_spec_class_generator(self):
        """Instantiated classes from spec_class_generator should equal their spec"""
        for spec in [self.add, self.add_three, self.add_two, self.multiply]:
            cls = spec_class_generator("cls", spec)
            self.assertEqual(cls(), spec)

    def test_empty_workflow(self):
        """Empty Workflow objects should have certain properties"""
        wf = specs.Workflow()

        self.assertEquals(len(wf), 5)
        self.assertEquals(set(wf.keys()), set(["mode", "steps",
                                               "connections", "inputs",
                                               "outputs"]))
        self.assertEquals(wf['mode'], "workflow")
        self.assertEquals(wf['steps'], [])
        self.assertEquals(wf['connections'], [])
        self.assertEquals(wf['inputs'], [])
        self.assertEquals(wf['outputs'], [])

        self.assertEquals(wf.mode, "workflow")
        self.assertEquals(wf.steps, [])
        self.assertEquals(wf.connections, [])
        self.assertEquals(wf.inputs, [])
        self.assertEquals(wf.outputs, [])

        with self.assertRaises(specs.ReadOnlyAttributeException):
            del wf['mode']

        with self.assertRaises(KeyError):
            del wf['foo']

        with self.assertRaises(specs.ReadOnlyAttributeException):
            wf['mode'] = "foo"

        with self.assertRaises(KeyError):
            wf['foo']

        with self.assertRaises(KeyError):
            wf['foo'] = "foo"

    def test_workflow_add_task_dict(self):
        """Adding task dicts should show up in Workflow.steps"""
        wf = specs.Workflow()

        wf.add_task(self.add, "add")
        task_list = [{"name": "add", "task": self.add}]
        # Steps should be equal to a list of dicts
        self.assertEquals(wf['steps'], task_list)
        self.assertEquals(wf.steps, task_list)

        # Steps should be equal to a list of Spec() dicts
        self.assertEquals(wf['steps'], [specs.Spec(t) for t in task_list])
        self.assertEquals(wf.steps, [specs.Spec(t) for t in task_list])

        # Steps should be equal to a list of StepSpec() dicts
        self.assertEquals(wf['steps'], [specs.StepSpec(t) for t in task_list])
        self.assertEquals(wf.steps, [specs.StepSpec(t) for t in task_list])

        # No duplicate nodes
        with self.assertRaises(specs.DuplicateTaskException):
            wf.add_task(self.add, "add")

        # Test with multiple tasks of the same type (different name)
        wf.add_task(self.add, "add2")
        task_list += [{"name": "add2", "task": self.add}]

        self.assertEquals(to_frozenset(wf['steps']), to_frozenset(task_list))
        self.assertEquals(to_frozenset(wf.steps), to_frozenset(task_list))

        self.assertEquals(to_frozenset(wf['steps']),
                          to_frozenset([specs.Spec(t) for t in task_list]))
        self.assertEquals(to_frozenset(wf.steps),
                          to_frozenset([specs.Spec(t) for t in task_list]))

        # Steps should be equal to a list of StepSpec() dicts
        self.assertEquals(to_frozenset(wf['steps']),
                          to_frozenset([specs.StepSpec(t) for t in task_list]))
        self.assertEquals(to_frozenset(wf.steps),
                          to_frozenset([specs.StepSpec(t) for t in task_list]))

    def test_workflow_connect_tasks(self):
        """Verify connections is correct given a known task graph"""
        #################################################################
        #                          Task Graph
        #                        ==============
        #
        #        +               +          +              +
        # {in1}  |        {in2}  |          | {a}          | {b}
        #        |               |          |              |
        #        +--^---------+^-+          +-^---------+ <+
        #           |         |               |         |
        #           |    M1   |               |   A1    |
        #           |         |               |         |
        #           +----+----+               +-----+---+
        #                |                          |
        #          {out} |                          |  {c}
        #                |                          |
        #                |       +-----------+      |
        #                |       |           |      |
        #                +------^+           +^-----+
        #                  {in1} |    M2     |  {in2}
        #                        |           |
        #                        +-----+-----+                  ^
        #                              |                        |
        #                        {out} |                        |
        #                              |                        |
        #                              |    +------------+      |
        #                              |    |            |      |
        #                              +---^+            +------+
        #                              {a}  |    A2      |   {b}
        #                                   |            |
        #                                   +-----+------+
        #                                         |
        #                                         |  {c}
        #                                         |
        #                                         v
        #################################################################
        wf = specs.Workflow()

        wf.add_task(self.multiply, "m1")
        wf.add_task(self.multiply, "m2")
        wf.add_task(self.add, "a1")
        wf.add_task(self.add, "a2")

        wf.connect_tasks("m1", "m2", {"out": "in1"})
        wf.connect_tasks("a1", "m2", {"c": "in2"})
        wf.connect_tasks("m2", "a2", {"out": "a"})

        ground = [{"input": "a", "input_step": "a1", "name": "a"},
                  {"input": "b", "input_step": "a1", "name": "a1.b"},
                  {"input": "b", "input_step": "a2", "name": "a2.b"},
                  {"input": "in1", "input_step": "m1", "name": "in1"},
                  {"input": "in2", "input_step": "m1", "name": "in2"},
                  {"input": "in2", "input_step": "m2",
                   "output": "c", "output_step": "a1"},
                  {"input": "in1", "input_step": "m2",
                   "output": "out", "output_step": "m1"},
                  {"input": "a", "input_step": "a2",
                   "output": "out", "output_step": "m2"},
                  {"name": "c", "output": "c", "output_step": "a2"}]

        self.assertEquals(to_frozenset(wf.connections), to_frozenset(ground))

        self.assertEquals(to_frozenset(wf.connections),
                          to_frozenset([specs.Spec(d) for d in ground]))

        self.assertEquals(to_frozenset(wf.connections),
                          to_frozenset([specs.ConnectionSpec(d) for d in ground]))


    # Test connect_tasks(t1, t2, {"output": input})

    # Test connect_tasks(t1, t2, output="input")

    # Test connect_tasks((t1, t2, {"output", "input"}), (t3, t2, {"output", "input"}))




if __name__ == '__main__':
    unittest.main(verbosity=2)
