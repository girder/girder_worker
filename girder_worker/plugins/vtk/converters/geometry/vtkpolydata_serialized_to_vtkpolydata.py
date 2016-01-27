import vtk

reader = vtk.vtkPolyDataReader()
reader.ReadFromInputStringOn()
reader.SetInputString(input, len(input))
reader.Update()
output = reader.GetOutput()
