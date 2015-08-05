import vtk

writer = vtk.vtkTableWriter()
writer.WriteToOutputStringOn()
writer.SetInputData(input)
writer.Update()
output = writer.GetOutputString()
