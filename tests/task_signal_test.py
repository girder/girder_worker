import unittest
import mock

from girder_worker.app import (
    gw_task_prerun,
    gw_task_success,
    gw_task_failure,
    gw_task_postrun)

from girder_worker.utils import JobStatus


class TestSignals(unittest.TestCase):
    def setUp(self):
        self.headers = {
            'jobInfoSpec': {
                'method': 'PUT',
                'url': 'http://girder:8888/api/v1',
                'reference': 'JOBINFOSPECREFERENCE',
                'headers': {'Girder-Token': 'GIRDERTOKEN'},
                'logPrint': True
            }
        }

    @mock.patch('girder_worker.utils.JobManager')
    def test_task_prerun(self, jm):
        task = mock.MagicMock()
        task.request.jobInfoSpec = self.headers['jobInfoSpec']
        task.request.parent_id = None

        gw_task_prerun(task=task)

        task.job_manager.updateStatus.assert_called_once_with(
            JobStatus.RUNNING)

    @mock.patch('girder_worker.utils.JobManager')
    def test_task_success(self, jm):
        task = mock.MagicMock()
        task.request.parent_id = None
        task.job_manager = jm(**self.headers)

        gw_task_success(sender=task)

        task.job_manager.updateStatus.assert_called_once_with(
            JobStatus.SUCCESS)

    @mock.patch('girder_worker.utils.JobManager')
    def test_task_failure(self, jm):
        task = mock.MagicMock()
        task.request.parent_id = None
        task.job_manager = jm(**self.headers)

        exc, tb = mock.MagicMock(), mock.MagicMock()
        exc.__str__.return_value = 'MOCKEXCEPTION'

        with mock.patch('girder_worker.app.tb') as traceback:
            traceback.format_tb.return_value = 'TRACEBACK'

            gw_task_failure(sender=task, exception=exc, traceback=tb)

            task.job_manager.write.assert_called_once_with(
                'MagicMock: MOCKEXCEPTION\nTRACEBACK')
            task.job_manager.updateStatus(JobStatus.ERROR)

    @mock.patch('girder_worker.utils.JobManager')
    def test_task_postrun(self, jm):
        task = mock.MagicMock()
        task.request.parent_id = None
        task.job_manager = jm(**self.headers)

        gw_task_postrun(task=task)

        task.job_manager._flush.assert_called_once()
        task.job_manager._redirectPipes.assert_called_once_with(False)
