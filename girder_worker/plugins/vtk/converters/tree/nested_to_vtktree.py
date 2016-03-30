from girder_worker.plugins.vtk import dict_to_vtkarrays, dict_to_vtkrow
import vtk

vtk_builder = vtk.vtkMutableDirectedGraph()
node_fields = input['node_fields']
edge_fields = input['edge_fields']
dict_to_vtkarrays(input['node_data'], node_fields, vtk_builder.GetVertexData())
if 'children' in input and len(input['children']) > 0:
    if 'edge_data' in input['children'][0]:
        dict_to_vtkarrays(input['children'][0]['edge_data'], edge_fields,
                          vtk_builder.GetEdgeData())


def process_node(vtknode, node):
    if 'children' in node:
        for n in node['children']:
            vtkchild = vtk_builder.AddVertex()
            vtk_builder.AddGraphEdge(vtknode, vtkchild).GetId()
            dict_to_vtkrow(n['node_data'], vtk_builder.GetVertexData())
            if 'edge_data' in n:
                dict_to_vtkrow(n['edge_data'], vtk_builder.GetEdgeData())
            process_node(vtkchild, n)
vtk_builder.AddVertex()
dict_to_vtkrow(input['node_data'], vtk_builder.GetVertexData())
process_node(0, input)
output = vtk.vtkTree()
output.ShallowCopy(vtk_builder)
