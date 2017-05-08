"""This module defines the workflow pipeline object."""

from girder_worker.core.specs import PortList, ReadOnlyAttributeException, Spec

from collections import MutableMapping
import networkx as nx
import copy


class WorkflowException(Exception):
    """Exception thrown for issues with Workflows"""
    pass


class DuplicateTaskException(WorkflowException):
    """Exception thrown when adding a duplicate task"""
    pass


class StepSpec(Spec):
    def __init__(self, *args, **kwargs):
        super(StepSpec, self).__init__(*args, **kwargs)


StepSpec.make_property('name', 'Name of the step in the workflow')
StepSpec.make_property('task', 'Workflow task associated with this step')


class ConnectionSpec(Spec):
    def __init__(self, *args, **kwargs):
        super(ConnectionSpec, self).__init__(*args, **kwargs)


ConnectionSpec.make_property(
    'name', 'Workflow external facing input or output name')
ConnectionSpec.make_property('input', 'Name of input Port')
ConnectionSpec.make_property('input_step', 'Name of input step')
ConnectionSpec.make_property('output', 'Name of input Port')
ConnectionSpec.make_property('output_step', 'Name of output step')


class Workflow(MutableMapping):

    def __init__(self, *args, **kw):
        self.__graph__ = nx.DiGraph()

        self.__interface = {'mode', 'steps', 'connections',
                            'inputs', 'outputs'}
        self._defaults = {}

        self.mode = 'workflow'

    ##
    # Graph API
    #

    def _add_node(self, name, task):
        if name in self.__graph__.nodes():
            raise DuplicateTaskException('%s is already in Workflow!' % name)
        self.__graph__.add_node(name, task=task)

    def add_task(self, task, name=None):
        if hasattr(task, 'name'):
            self._add_node(task.name, task)
        elif name is not None:
            self._add_node(name, task)
        else:
            raise TypeError('If task does not have a name attribute, '
                            'name argument cannot be None.')
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
        """
        Connect two tasks together specifying which input ports connect
        to which output ports. This function takes either 1, 2 or 3 arguments.
        In the case of one argument it expects a list of tuples where the tuples
        are the first, second and third arguments to connect_tasks. If there are
        two arguments given they must be nodes in the workflow and ports must
        be specified as key word arguments.  If three arguments are supplied
        they should be node1, node2 and a dict of port connections where keys
        are the output ports on node1 and value are the input ports on node2.
        """

        # Single iterable argument - apply connect_tasks() to
        # each element in the iterable
        if len(args) == 1 and hasattr(args[0], '__iter__'):
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
            raise TypeError(
                'connect_tasks() takes either 3 arguments or an '
                'iterable of 3 argument tuples. (%s given)' % len(args))
    ##
    # Dict-like API
    #

    @property
    def steps(self):
        return [StepSpec({'name': n,  'task': dict(data['task'])})
                for n, data in self.__graph__.nodes(data=True)]

    def _get_connections_and_open_ports(self):
        """Internal function that returns three arguments. The first argument
        is a list of tuples of the form (output_node, output_port, input_node,
        input_port).  The second argument is a dict of open input ports. The
        third argument is a dict of open output ports.
        """

        # Generate sets of input/output ports indexed by node name
        # We will remove ports from these input/output sets as we
        # loop through the graph edge data.  This should leave us
        # with all 'open' input ports and all 'open' output ports
        input_ports = {}
        output_ports = {}
        for name, data in self.__graph__.nodes(data=True):
            input_ports[name] = set([d['name'] for d in data['task']['inputs']])
            output_ports[name] = set(
                [d['name'] for d in data['task']['outputs']])

        internal_connections = []
        for output_node, input_node, connections in self.__graph__.edges(
                data=True):
            for output_port, input_port in connections.items():

                # Add to internal connections set
                internal_connections.append((output_node, output_port,
                                             input_node, input_port))

                # Pop output_port off of output_node
                output_ports[output_node].remove(output_port)

                # Pop input_port off of input_node
                input_ports[input_node].remove(input_port)

        return internal_connections, input_ports, output_ports

    def _get_node_name(self, node, port, ports):
        """
        Return 'node.port' if there is any other port under a different node
        with the same name. Otherwise return 'port'.
        """
        if any(port in S for k, S in ports.items() if k != node):
            return '%s.%s' % (node, port)
        return port

    @property
    def connections(self):
        internal, input_ports, output_ports = (
            self._get_connections_and_open_ports())
        connections = []

        for node, inputs in input_ports.items():
            for input_port in inputs:
                connections.append(
                    ConnectionSpec({
                        'name': self._get_node_name(
                            node, input_port, input_ports),
                        'input_step': node,
                        'input': input_port
                    }))

        for output_node, output_port, input_node, input_port in internal:
            connections.append(
                ConnectionSpec({
                    'output_step': output_node,
                    'output': output_port,
                    'input_step': input_node,
                    'input': input_port
                }))

        for node, outputs in output_ports.items():
            for output_port in outputs:
                connections.append(
                    ConnectionSpec({
                        'name': self._get_node_name(
                            node, output_port, output_ports),
                        'output_step': node,
                        'output': output_port
                    }))

        return connections

    @property
    def inputs(self):
        _, open_port_names, _ = self._get_connections_and_open_ports()
        ports = []

        for node, port_names in open_port_names.items():

            # Hash the actual analysis imports by name
            input_ports = {v['name']: v for v in
                           self.__graph__.node[node]['task']['inputs']}

            # loop through open port names for this node
            for port_name in port_names:

                # Copy the actual analysis port
                port = copy.deepcopy(input_ports[port_name])

                # Set the port name (handles conflicts by prefixing with
                # node name)
                port['name'] = self._get_node_name(
                    node, port_name, open_port_names)

                # Check defaults
                if self.has_default(port['name']):
                    port['default'] = self.get_default(port['name'])

                ports.append(port)

        return PortList(ports)

    @property
    def outputs(self):
        _, _, open_port_names = self._get_connections_and_open_ports()
        ports = []

        for node, port_names in open_port_names.items():

            # Hash the actual analysis imports by name
            output_ports = {v['name']: v for v in
                            self.__graph__.node[node]['task']['outputs']}

            # loop through open port names for this node
            for port_name in port_names:

                # Copy the actual analysis port
                port = copy.deepcopy(output_ports[port_name])

                # Set the port name (handles conflicts by prefixing with
                # node name)
                port['name'] = self._get_node_name(
                    node, port_name, open_port_names)

                # Check defaults
                if self.has_default(port['name']):
                    port['default'] = self.get_default(port['name'])

                ports.append(port)

        return PortList(ports)

    def __getitem__(self, key):
        if key not in self.__interface:
            raise KeyError('Workflow keys must be one of %s' %
                           ', '.join(self.__interface))

        return getattr(self, key)

    def __setitem__(self, key, value):
        if key in self.__interface:
            raise ReadOnlyAttributeException(
                '%s should not be directly assigned')

        raise KeyError('Workflow keys must be one of %s' %
                       ', '.join(self.__interface))

    def __delitem__(self, key):
        if key in self.__interface:
            raise ReadOnlyAttributeException(
                '%s should not be directly removed')
        raise KeyError(key)

    def __len__(self):
        return len(self.__interface)

    def __iter__(self):
        for key in self.__interface:
            yield key

    #####
    #  Workflow API
    #

    # Implementing a full default wrapper because we may need
    # to support more sophisticated functionality down the line.
    # For example we may want to 'alais' external workflow port names
    # to internal open port names. This means we could set a default
    # on 'a2.a' and then later alais 'a2.a'  to 'x' the input port
    # would still need to look like {name: 'x', default: {....}, ...}
    # even though we set the default on 'a2.a.' to support something like
    # that we need a consistent CRUD-like API around self._defaults.

    def set_default(self, node_name, default):
        # TODO create DefaultSpec and wrap assignment here
        self._defaults[node_name] = default

    def get_default(self, node_name):
        return self._defaults[node_name]

    def has_default(self, node_name):
        return node_name in self._defaults.keys()

    def remove_default(self, node_name):
        try:
            del self._defaults[node_name]
        except KeyError:
            pass


__all__ = ('Workflow', 'StepSpec', 'ConnectionSpec')
