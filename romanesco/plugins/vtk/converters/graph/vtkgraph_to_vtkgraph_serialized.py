import vtk

writer = vtk.vtkGraphWriter()
writer.WriteToOutputStringOn()
writer.SetInputData(input)
writer.Update()
output = writer.GetOutputString()
