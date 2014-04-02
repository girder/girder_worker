from romanesco.format import dict_to_vtkarrays, dict_to_vtkrow
import vtk

vtk_builder = vtk.vtkMutableDirectedGraph()
dict_to_vtkarrays(input["node_data"], vtk_builder.GetVertexData())
if "children" in input and len(input["children"]) > 0:
    dict_to_vtkarrays(input["children"][0]["edge_data"], vtk_builder.GetEdgeData())
def process_node(vtknode, node):
    if "children" in node:
        for n in node["children"]:
            vtkchild = vtk_builder.AddVertex()
            vtkparentedge = vtk_builder.AddGraphEdge(vtknode, vtkchild).GetId()
            dict_to_vtkrow(n["node_data"], vtk_builder.GetVertexData())
            dict_to_vtkrow(n["edge_data"], vtk_builder.GetEdgeData())
            process_node(vtkchild, n)
vtk_builder.AddVertex()
dict_to_vtkrow(input["node_data"], vtk_builder.GetVertexData())
process_node(0, input)
output = vtk.vtkTree()
output.ShallowCopy(vtk_builder)
