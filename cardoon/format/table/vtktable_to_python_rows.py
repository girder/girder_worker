from cardoon.format import vtkrow_to_dict
output = []
for r in range(input.GetNumberOfRows()):
    output.append(vtkrow_to_dict(input.GetRowData(), r))
