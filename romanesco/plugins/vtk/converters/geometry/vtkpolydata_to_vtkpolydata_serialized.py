import vtk

writer = vtk.vtkPolyDataWriter()
writer.WriteToOutputStringOn()
writer.SetInputData(input)
writer.Update()
output = writer.GetOutputString()
