import vtk

tmp = tempfile.mktemp()
writer = vtk.vtkTreeWriter()
writer.SetFileName(tmp)
writer.SetFileTypeToBinary()
writer.SetInputData(input)
writer.Update()
with open(tmp, 'r') as fp:
    output = fp.read()
os.remove(tmp)
