from girder_worker.plugins.vtk import dict_to_vtkarrays, dict_to_vtkrow
import six
import vtk

"""
NetworkX to vtkGraph

This creates a vtkMutableDirectedGraph or vtkMutableUndirectedGraph.

It creates nodes which lose their actual value since nodes in vtkGraph
are referenced strictly by their index. These nodes do retain metadata
in the same way edges do (see below).

It creates edges which maintain the proper association and any metadata,
the caveat is that all edges are given all metadata attributes with
default values.

So if an edge has an integer 'distance' attribute, and another does not - the
non-distanced edge will have a distance of 0. This follows suit for
all of python's defaults, bool(), str(), float(), etc.

As such it requires that all keys have the same type.
"""

if input.is_directed():
    output = vtk.vtkMutableDirectedGraph()
else:
    output = vtk.vtkMutableUndirectedGraph()

nodes = input.nodes(data=True)
edges = input.edges(data=True)
edge_field_types = {}
node_field_types = {}

# Find out fields and types
for (_, data) in nodes:
    for key in data.keys():
        data_type = type(data[key])

        # Assert that every node which has key has the same type
        if key in node_field_types and data_type != node_field_types[key]:
            raise Exception('Node has heterogeneous types for key %s' % key)

        node_field_types[key] = data_type

for (_, _, data) in edges:
    for key in data.keys():
        data_type = type(data[key])

        # Assert that every edge which has key has the same type
        if key in edge_field_types and data_type != edge_field_types[key]:
            raise Exception('Edge has heterogeneous types for key %s' % key)

        edge_field_types[key] = data_type

# Merge default attributes into nodes and edges
for (_, data) in nodes:
    for (field, field_type) in six.iteritems(node_field_types):
        if field not in data:
            data[field] = field_type()

for (_, _, data) in edges:
    for (field, field_type) in six.iteritems(edge_field_types):
        if field not in data:
            data[field] = field_type()

# Add vtkArrays to the output data for nodes and edges
# We can just use the first node and edge since they all have same
# attr name/types
if nodes:
    dict_to_vtkarrays(nodes[0][1],
                      node_field_types.keys(),
                      output.GetVertexData())

if edges:
    dict_to_vtkarrays(edges[0][2],
                      edge_field_types.keys(),
                      output.GetEdgeData())


# This is a mapping of NetworkX nodes to VTK Vertex IDs so we can refer to them
# when adding edges between NetworkX nodes later
node_to_ids = {}

for (node, data) in nodes:
    node_to_ids[node] = output.AddVertex()
    dict_to_vtkrow(data, output.GetVertexData())

for (u, v, data) in edges:
    output.AddGraphEdge(node_to_ids[u], node_to_ids[v])
    dict_to_vtkrow(data, output.GetEdgeData())
