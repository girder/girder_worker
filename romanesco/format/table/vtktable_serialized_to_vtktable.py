import vtk
reader = vtk.vtkTableReader()
reader.ReadFromInputStringOn()
reader.SetInputString(input, len(input))
reader.Update()
output = reader.GetOutput()
