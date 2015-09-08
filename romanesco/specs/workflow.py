"""This module defines the workflow pipeline object."""

# import six

# import romanesco
from romanesco.specs import PortList, ReadOnlyAttributeException

from collections import MutableMapping
import networkx as nx


class Workflow(MutableMapping):

    def __init__(self, *args, **kw):
        self.__graph__ = nx.DiGraph()

        self.__interface = {"mode", "steps", "connections",
                            "inputs", "outputs"}
        self.mode = "workflow"

    @property
    def steps(self):
        return []

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


__all__ = ("Workflow", )
