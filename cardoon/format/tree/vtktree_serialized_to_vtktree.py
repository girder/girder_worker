import vtk

reader = vtk.vtkTreeReader()
reader.ReadFromInputStringOn()
reader.SetBinaryInputString(input, len(input))
reader.Update()
output = reader.GetOutput()
