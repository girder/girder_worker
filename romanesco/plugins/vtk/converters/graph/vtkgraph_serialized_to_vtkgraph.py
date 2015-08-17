import vtk

reader = vtk.vtkGraphReader()
reader.ReadFromInputStringOn()
reader.SetInputString(input, len(input))
reader.Update()
output = reader.GetOutput()
