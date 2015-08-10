from romanesco.plugins.vtk import dict_to_vtkarrays, dict_to_vtkrow
import vtk

if input.is_directed():
    output = vtk.vtkMutableDirectedGraph()
else:
    output = vtk.vtkMutableUndirectedGraph()

node_fields = input.nodes(data=True)[0][1].keys()
edge_fields = input.edges(data=True)[0][2].keys()

# assume all edges have the same metadata specified, and that it is the same type
dict_to_vtkarrays(input.nodes(data=True)[0][1], node_fields, output.GetVertexData())
dict_to_vtkarrays(input.edges(data=True)[0][2], edge_fields, output.GetEdgeData())

# This is a mapping of NetworkX nodes to VTK Vertex IDs so we can refer to them
# when adding edges between NetworkX nodes later
nodes = {}

for (node, data) in input.nodes(data=True):
    nodes[node] = output.AddVertex()
    dict_to_vtkrow(data, output.GetVertexData())

for (u, v, data) in input.edges(data=True):
    output.AddGraphEdge(nodes[u], nodes[v])
    dict_to_vtkrow(data, output.GetEdgeData())
