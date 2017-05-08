from tempfile import mktemp
from girder_worker.tasks import run
import girder_worker
import os
import unittest

_tmpfiles = []


def _mockTempfile():
    global _tmpfiles
    out = mktemp()
    _tmpfiles.append(out)
    return out


girder_worker.core.executors.python.tempfile.mktemp = _mockTempfile


class TestDebug(unittest.TestCase):

    def setUp(self):
        global _tmpfiles
        _tmpfiles = []

        self.script = (
            "c = {'fields': a['fields'], 'rows': a['rows'] + b['rows']}"
        )
        self.analysis = {
            'name': 'append_tables',
            'inputs': [
                {'name': 'a', 'type': 'table', 'format': 'rows'},
                {'name': 'b', 'type': 'table', 'format': 'rows'}
            ],
            'outputs': [{'name': 'c', 'type': 'table', 'format': 'rows'}],
            'script': self.script,
            'mode': 'python'
        }

        self.inputs = {
            'a': {
                'format': 'rows.json',
                'data': ('{"fields": ["aa", "bb"], '
                         '"rows": [{"aa": 1, "bb": 2}]}')
            },
            'b': {
                'format': 'rows.json',
                'data': ('{"fields": ["aa", "bb"],'
                         '"rows": [{"aa": 3, "bb": 4}]}')
            }
        }

        self.outputs = {
            'c': {'format': 'rows.json'}
        }

        # Change dir for loading analyses
        self.prevdir = os.getcwd()
        cur_path = os.path.dirname(os.path.realpath(__file__))
        os.chdir(cur_path)
        self.analysis_path = os.path.join(cur_path, '..', 'analysis')

    def tearDown(self):
        os.chdir(self.prevdir)

    def test_analysis_debug(self):
        """Runs the table json test but with asserts for analysis debugging"""
        global _tmpfiles

        run(
            dict(self.analysis.items() + [('write_script', 1)]),
            inputs=self.inputs, outputs=self.outputs)

        # Should have generated just one debug file
        self.assertEquals(len(_tmpfiles), 1)

        # File contents equals script
        with open(_tmpfiles[0], 'r') as fh:
            self.assertEquals(fh.read(), self.script)

    def test_kwargs_debug(self):
        """Runs the table json test but with asserts for kwarg debugging"""
        global _tmpfiles

        run(
            self.analysis, self.inputs, self.outputs, write_script=True)

        # Should have generated serveral files ()
        self.assertGreater(len(_tmpfiles), 1)
