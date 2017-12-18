from girder_worker.tasks import run
import os
import shutil
import tarfile
import unittest
import zipfile

DATA_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')


class TestDirectory(unittest.TestCase):
    """
    Tests the conversions for the directory type formats.
    """
    extractTask = {
        'inputs': [{
            'id': 'myDir',
            'type': 'directory',
            'format': 'path'
        }],
        'outputs': [{
            'id': 'myDir',
            'type': 'string',
            'format': 'text'
        }, {
            'name': 'files',
            'type': 'python',
            'format': 'object'
        }],
        'script': '\n'.join([
            'import os',
            'files = list(os.listdir(myDir))'
        ]),
        'mode': 'python'
    }

    zipFile = os.path.join(DATA_DIR, 'testZip.zip')
    zipDir = os.path.join(DATA_DIR, 'testZip')
    tarFile = os.path.join(DATA_DIR, 'testTar.tar.gz')
    tarDir = os.path.join(DATA_DIR, 'testTar.tar')
    createFromDir = os.path.join(DATA_DIR, 'shapefile')

    def setUp(self):
        self._cleanArchiveData()

    def tearDown(self):
        self._cleanArchiveData()

    def _cleanArchiveData(self):
        if os.path.exists(self.zipDir):
            shutil.rmtree(self.zipDir)
        if os.path.exists(self.tarDir):
            shutil.rmtree(self.tarDir)
        if os.path.exists(self.createFromDir + '.zip'):
            os.remove(self.createFromDir + '.zip')
        if os.path.exists(self.createFromDir + '.tgz'):
            os.remove(self.createFromDir + '.tgz')

    def testExtractZip(self):
        outputs = run(
            self.extractTask,
            inputs={
                'myDir': {
                    'format': 'zip',
                    'data': self.zipFile
                }
            })

        self.assertEqual(set(outputs['files']['data']),
                         set(('provision.retry', 'site.retry')))
        self.assertEqual(outputs['myDir']['data'], self.zipDir)
        self.assertTrue(os.path.isdir(self.zipDir))
        self.assertTrue(
            os.path.isfile(os.path.join(self.zipDir, 'site.retry')))
        self.assertTrue(
            os.path.isfile(os.path.join(self.zipDir, 'provision.retry')))

    def testExtractTgz(self):
        outputs = run(
            self.extractTask,
            inputs={
                'myDir': {
                    'format': 'tgz',
                    'data': self.tarFile
                }
            })

        self.assertEqual(set(outputs['files']['data']),
                         set(('provision.retry', 'site.retry')))
        self.assertEqual(outputs['myDir']['data'], self.tarDir)
        self.assertTrue(os.path.isdir(self.tarDir))
        self.assertTrue(
            os.path.isfile(os.path.join(self.tarDir, 'site.retry')))
        self.assertTrue(
            os.path.isfile(os.path.join(self.tarDir, 'provision.retry')))

    def testCreateZip(self):
        task = {
            'inputs': [{
                'id': 'myArchive',
                'type': 'directory',
                'format': 'zip'
            }],
            'outputs': [{
                'id': 'output',
                'type': 'string',
                'format': 'text'
            }],
            'script': 'output = myArchive',
            'mode': 'python'
        }

        outputs = run(task, inputs={
            'myArchive': {
                'format': 'path',
                'data': self.createFromDir
            }
        })

        path = outputs['output']['data']
        self.assertEqual(path, os.path.join(DATA_DIR, 'shapefile.zip'))
        self.assertTrue(os.path.isfile(path))
        with zipfile.ZipFile(path, 'r') as zf:
            names = zf.namelist()
            self.assertTrue('shapefile/shapefile.cpg' in names)
            self.assertTrue('shapefile/shapefile.prj' in names)

    def testCreateTgz(self):
        task = {
            'inputs': [{
                'id': 'myArchive',
                'type': 'directory',
                'format': 'tgz'
            }],
            'outputs': [{
                'id': 'output',
                'type': 'string',
                'format': 'text'
            }],
            'script': 'output = myArchive',
            'mode': 'python'
        }

        outputs = run(task, inputs={
            'myArchive': {
                'format': 'path',
                'data': self.createFromDir
            }
        })

        path = outputs['output']['data']
        self.assertEqual(path, os.path.join(DATA_DIR, 'shapefile.tgz'))
        self.assertTrue(os.path.isfile(path))
        with tarfile.open(path, 'r') as tf:
            names = tf.getnames()
            self.assertTrue('shapefile/shapefile.cpg' in names)
            self.assertTrue('shapefile/shapefile.prj' in names)


if __name__ == '__main__':
    unittest.main()
