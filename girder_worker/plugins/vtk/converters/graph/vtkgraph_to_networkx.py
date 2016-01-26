import vtk
import networkx as nx
from girder_worker.plugins.vtk import vtkrow_to_dict

directed = isinstance(input, vtk.vtkMutableDirectedGraph)
output = nx.DiGraph() if directed else nx.Graph()

# Add nodes
for node in range(input.GetNumberOfVertices()):
    output.add_node(node, vtkrow_to_dict(input.GetVertexData(), node))

# Add edges
for edge in range(input.GetNumberOfEdges()):
    output.add_edge(input.GetSourceVertex(edge),
                    input.GetTargetVertex(edge),
                    attr_dict=vtkrow_to_dict(input.GetEdgeData(), edge))
