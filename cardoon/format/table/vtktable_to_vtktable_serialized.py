import os
import tempfile
import vtk

tmp = tempfile.mktemp()
writer = vtk.vtkTableWriter()
writer.SetFileName(tmp)
writer.SetFileTypeToBinary()
writer.SetInputData(input)
writer.Update()
with open(tmp, 'r') as fp:
    output = fp.read()
os.remove(tmp)
