from romanesco.format import dict_to_vtkarrays, dict_to_vtkrow
import vtk

output = vtk.vtkTable()
if len(input) > 0:
    dict_to_vtkarrays(input[0], output.GetRowData())
    for d in input:
        dict_to_vtkrow(d, output.GetRowData())
