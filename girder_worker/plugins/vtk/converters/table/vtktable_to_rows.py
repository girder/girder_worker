from girder_worker.plugins.vtk import vtkrow_to_dict

output = {'fields': [], 'rows': []}
for c in range(input.GetNumberOfColumns()):
    output['fields'].append(input.GetColumnName(c))
for r in range(input.GetNumberOfRows()):
    output['rows'].append(vtkrow_to_dict(input.GetRowData(), r))
