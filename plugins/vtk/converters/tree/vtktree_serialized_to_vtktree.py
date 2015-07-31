import vtk

reader = vtk.vtkTreeReader()
reader.ReadFromInputStringOn()
reader.SetInputString(input, len(input))
reader.Update()
output = reader.GetOutput()
