import unittest
import mock

from girder_worker.app import (
    girder_before_task_publish,
    gw_task_prerun,
    gw_task_success,
    gw_task_failure,
    gw_task_postrun)

from contextlib import contextmanager
from girder_worker.utils import JobStatus


@contextmanager
def mock_worker_plugin_utils():
    """girder.plugins is not available unless you are
    working within the context of a rest request. This
    context manager allows us to mock girder.plugins.worker.utils
    without seting up a whole server.
    """

    girder_plugins = mock.MagicMock()
    with mock.patch.dict('sys.modules',
                         **{'girder.plugins': mock.MagicMock(),
                            'girder.plugins.worker': girder_plugins}):
        with mock.patch.object(girder_plugins, 'utils') as utils:
            yield utils


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

    @mock.patch('girder.utility.model_importer.ModelImporter')
    @mock.patch('girder.api.rest.getCurrentUser')
    def test_girder_before_task_publish_with_jobinfospec_no_job_created(self, gcu, mi):

        inputs = dict(sender='test.task',
                      # args, kwargs, options
                      body=[(), {}, {}],
                      headers=self.headers)

        create_job = mi.model.return_value.createJob

        with mock_worker_plugin_utils():
            girder_before_task_publish(**inputs)

        self.assertTrue(not gcu.called)
        self.assertTrue(not create_job.called)

    @mock.patch('girder.utility.model_importer.ModelImporter')
    @mock.patch('girder.api.rest.getCurrentUser')
    def test_girder_before_task_publish_called_with_no_headers_create_job_inputs(self, gcu, mi):

        inputs = dict(sender='test.task',
                      # args, kwargs, options
                      body=[(), {}, {}],
                      headers={'id': 'CELERY-ASYNCRESULT-ID'})

        create_job = mi.model.return_value.createJob

        with mock_worker_plugin_utils():
            girder_before_task_publish(**inputs)

        gcu.assert_called_once()
        create_job.assert_called_once_with(
            **{'title': None,
               'type': None,
               'handler': 'celery_handler',
               'public': False,
               'user': gcu.return_value,
               'args': (),
               'kwargs': {},
               'otherFields': {'celeryTaskId': 'CELERY-ASYNCRESULT-ID'}})

    @mock.patch('girder.utility.model_importer.ModelImporter')
    @mock.patch('girder.api.rest.getCurrentUser')
    def test_girder_before_task_publish_called_with_headers_create_job_inputs(self, gcu, mi):

        inputs = dict(sender='test.task',
                      # args, kwargs, options
                      body=[(), {}, {}],
                      headers={'id': 'CELERY-ASYNCRESULT-ID',
                               'girder_job_title': 'GIRDER_JOB_TITLE',
                               'girder_job_type': 'GIRDER_JOB_TYPE',
                               'girder_job_handler': 'GIRDER_JOB_HANDLER',
                               'girder_job_public': 'GIRDER_JOB_PUBLIC',
                               'girder_job_other_fields': {'SOME_OTHER': 'FIELD'}})

        create_job = mi.model.return_value.createJob

        with mock_worker_plugin_utils():
            girder_before_task_publish(**inputs)

        gcu.assert_called_once()
        create_job.assert_called_once_with(
            **{'title': 'GIRDER_JOB_TITLE',
               'type': 'GIRDER_JOB_TYPE',
               'handler': 'GIRDER_JOB_HANDLER',
               'public': 'GIRDER_JOB_PUBLIC',
               'user': gcu.return_value,
               'args': (),
               'kwargs': {},
               'otherFields': {'celeryTaskId': 'CELERY-ASYNCRESULT-ID',
                               'SOME_OTHER': 'FIELD'}})

    @mock.patch('girder.utility.model_importer.ModelImporter')
    @mock.patch('girder.api.rest.getCurrentUser')
    def test_girder_before_task_publish_jobinfospec_called(self, gcu, mi):

        inputs = dict(sender='test.task',
                      # args, kwargs, options
                      body=[(), {}, {}],
                      headers={'id': 'CELERY-ASYNCRESULT-ID'})

        with mock_worker_plugin_utils() as utils:
            girder_before_task_publish(**inputs)

            utils.jobInfoSpec.asset_called_once()
            utils.getWorkerApiUrl.assert_called_once()

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
