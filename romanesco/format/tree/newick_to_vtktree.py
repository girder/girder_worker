import vtk
reader = vtk.vtkNewickTreeReader()
reader.SetReadFromInputString(True)
reader.SetInputString(input, len(input))
reader.Update()
output = reader.GetOutput()
