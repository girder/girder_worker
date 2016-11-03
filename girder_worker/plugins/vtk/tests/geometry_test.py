from girder_worker.tasks import run, convert
import unittest
import vtk


class TestGeometry(unittest.TestCase):

    def setUp(self):
        self.cone = {
            'inputs': [
                {
                    'name': 'resolution',
                    'type': 'number',
                    'format': 'number'
                },
                {
                    'name': 'radius',
                    'type': 'number',
                    'format': 'number'
                }
            ],
            'outputs': [
                {
                    'name': 'cone',
                    'type': 'geometry',
                    'format': 'vtkpolydata'
                }
            ],
            'script': '\n'.join([
                'import vtk',
                'source = vtk.vtkConeSource()',
                'source.SetResolution(resolution)',
                'source.SetRadius(radius)',
                'source.Update()',
                'cone = source.GetOutput()'
            ]),
            'mode': 'python'
        }

    def test_cone(self):
        outputs = run(
            self.cone,
            inputs={
                'resolution': {'format': 'number', 'data': 100},
                'radius': {'format': 'number', 'data': 1}
            })
        self.assertEqual(outputs['cone']['format'], 'vtkpolydata')
        cone = outputs['cone']['data']
        self.assertTrue(isinstance(cone, vtk.vtkPolyData))
        self.assertEqual(cone.GetNumberOfCells(), 101)
        self.assertEqual(cone.GetNumberOfPoints(), 101)

    def test_convert(self):
        outputs = run(
            self.cone,
            inputs={
                'resolution': {'format': 'number', 'data': 100},
                'radius': {'format': 'number', 'data': 1}
            },
            outputs={
                'cone': {'format': 'vtkpolydata.serialized'}
            })
        cone = outputs['cone']['data']
        self.assertTrue(isinstance(cone, str))
        converted = convert(
            'geometry',
            outputs['cone'],
            {'format': 'vtkpolydata'}
        )['data']
        self.assertTrue(isinstance(converted, vtk.vtkPolyData))
        self.assertEqual(converted.GetNumberOfCells(), 101)
        self.assertEqual(converted.GetNumberOfPoints(), 101)

if __name__ == '__main__':
    unittest.main()
