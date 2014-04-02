import vtk
reader = vtk.vtkTableReader()
reader.ReadFromInputStringOn()
reader.SetBinaryInputString(input, len(input))
reader.Update()
output = reader.GetOutput()