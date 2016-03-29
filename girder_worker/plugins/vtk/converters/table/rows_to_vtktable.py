from girder_worker.plugins.vtk import dict_to_vtkarrays, dict_to_vtkrow
import vtk

output = vtk.vtkTable()
if len(input['rows']) > 0:
    dict_to_vtkarrays(input['rows'][0], input['fields'], output.GetRowData())
    for d in input['rows']:
        dict_to_vtkrow(d, output.GetRowData())
