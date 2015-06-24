import romanesco
import os
import shutil
import unittest

DATA_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')


class TestDirectory(unittest.TestCase):
    """
    Tests the conversions for the directory type formats.
    """

    def setUp(self):
        self.task = {
            "inputs": [{
                "id": "myDir",
                "type": "directory",
                "format": "path"
            }],
            "outputs": [{
                "id": "myDir",
                "type": "string",
                "format": "text"
            }, {
                "name": "files",
                "type": "python",
                "format": "object"
            }],
            "script": "\n".join([
                "import os",
                "files = list(os.listdir(myDir))"
            ]),
            "mode": "python"
        }

        self.zipFile = os.path.join(DATA_DIR, 'testZip.zip')
        self.zipDir = os.path.join(DATA_DIR, 'testZip')
        self.tarFile = os.path.join(DATA_DIR, 'testTar.tar.gz')
        self.tarDir = os.path.join(DATA_DIR, 'testTar.tar')

        self._cleanExtractedData()

    def tearDown(self):
        self._cleanExtractedData()

    def _cleanExtractedData(self):
        if os.path.exists(self.zipDir):
            shutil.rmtree(self.zipDir)
        if os.path.exists(self.tarDir):
            shutil.rmtree(self.tarDir)

    def testExtractZip(self):
        outputs = romanesco.run(
            self.task,
            inputs={
                "myDir": {
                    "format": "zip",
                    "data": self.zipFile
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
        outputs = romanesco.run(
            self.task,
            inputs={
                "myDir": {
                    "format": "tgz",
                    "data": self.tarFile
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


if __name__ == '__main__':
    unittest.main()
