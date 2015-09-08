"""This module defines the workflow pipeline object."""

# import six

# import romanesco
from romanesco.specs import PortList, ReadOnlyAttributeException, Spec

from collections import MutableMapping
import networkx as nx


class WorkflowException(Exception):
    """Exception thrown for issues with Workflows"""
    pass


class DuplicateTaskException(WorkflowException):
    """Exception thrown when adding a duplicate task"""
    pass


class StepSpec(Spec):
    def __init__(self, *args, **kwargs):
        super(StepSpec, self).__init__(*args, **kwargs)

StepSpec.make_property("name", "Name of the step in the workflow")
StepSpec.make_property("task", "Workflow task associated with this step")


class Workflow(MutableMapping):

    def __init__(self, *args, **kw):
        self.__graph__ = nx.DiGraph()

        self.__interface = {"mode", "steps", "connections",
                            "inputs", "outputs"}
        self.mode = "workflow"

    ##
    # Graph API
    #

    def _add_node(self, name, task):
        if name in self.__graph__.nodes():
            raise DuplicateTaskException("%s is already in Workflow!" % name)
        self.__graph__.add_node(name, data=task)

    def add_task(self, task, name=None):
        if hasattr(task, "name"):
            self._add_node(task.name, task)
        elif name is not None:
            self._add_node(name, task)
        else:
            raise TypeError("If task does not have a name attribute, "
                            "name argument cannot be None.")
        pass

    def add_tasks(self, tasks):
        for task in tasks:
            if isinstance(task, tuple):
                self.add_task(*task)
            else:
                self.add_task(task)

    def _add_edge(self, t1, t2, metadata):
        # metadata must be a dict
        # TODO: add validation for arg0 and arg1 inputs/outputs
        self.__graph__.add_edge(t1, t2, metadata)

    def connect_tasks(self, *args, **kwargs):
        """"""
        # Single iterable argument - apply connect_tasks() to
        # each element in the iterable
        if len(args) == 1 and hasattr("__iter__", args[0]):
            for arg in args[0]:
                self.connect_tasks(*arg)

        # Two arguments,  assume metadata is contained in kwargs
        # _add_edge will raise an exception if this is not the case
        elif len(args) == 2:
            kwargs = kwargs if kwargs is not None else {}
            self._add_edge(args[0], args[1], kwargs)

        # Three arguments,  assume these are t1, t2 and a dict of edge data
        elif len(args) == 3:
            # Update metadata dict with key word arguments if kwargs is not None
            if kwargs is not None:
                args[2].update(kwargs)

            self._add_edge(*args)
        else:
            raise TypeError("connect_tasks() takes either 3 arguments or an "
                            "iterable of 3 argument tuples. (%s given)" % len(args))
    ##
    # Dict-like API
    #

    @property
    def steps(self):
        return [StepSpec({"name": n,  "task": dict(props['data'])})
                for n, props in self.__graph__.nodes(data=True)]

    @property
    def connections(self):
        return []

    @property
    def inputs(self):
        return PortList()

    @property
    def outputs(self):
        return PortList()

    def __getitem__(self, key):
        if key not in self.__interface:
            raise KeyError("Workflow keys must be one of %s" %
                           ", ".join(self.__interface))

        return getattr(self, key)

    def __setitem__(self, key, value):
        if key in self.__interface:
            raise ReadOnlyAttributeException("%s should not be directly assigned")

        raise KeyError("Workflow keys must be one of %s" %
                       ", ".join(self.__interface))

    def __delitem__(self, key):
        if key in self.__interface:
            raise ReadOnlyAttributeException("%s should not be directly removed")
        raise KeyError(key)

    def __len__(self):
        return len(self.__interface)

    def __iter__(self):
        for key in self.__interface:
            yield key


__all__ = ("Workflow", "StepSpec", )
