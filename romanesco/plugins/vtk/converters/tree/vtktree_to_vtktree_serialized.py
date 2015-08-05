import vtk

writer = vtk.vtkTreeWriter()
writer.WriteToOutputStringOn()
writer.SetInputData(input)
writer.Update()
output = writer.GetOutputString()
