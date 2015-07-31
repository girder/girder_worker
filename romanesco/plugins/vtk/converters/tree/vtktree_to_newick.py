import vtk

writer = vtk.vtkNewickTreeWriter()
writer.SetWriteToOutputString(True)
writer.SetInputData(input)
writer.Update()
output = writer.GetOutputString()
