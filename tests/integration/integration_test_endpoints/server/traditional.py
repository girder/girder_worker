import copy
from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, filtermodel
from girder.utility.model_importer import ModelImporter

from girder.plugins.worker import utils
from girder.plugins.worker.constants import PluginSettings

from common_tasks.test_tasks.cancel import cancelable

from celery.exceptions import TimeoutError
import multiprocessing
from girder_worker.utils import JobStatus

from .utilities import wait_for_status

class TraditionalTestEndpoints(Resource):
    def __init__(self):
        super(TraditionalTestEndpoints, self).__init__()

        self.route('POST', ('test_job_girder_worker_run',),
                   self.test_traditional_job_girder_worker_run)
        self.route('POST', ('test_job_custom_task_name',),
                   self.test_traditional_job_custom_task_name)
        self.route('POST', ('test_job_custom_task_name_fails',),
                   self.test_traditional_job_custom_task_name_fails)
        self.route('POST', ('test_job_girder_worker_run_fails',),
                   self.test_traditional_job_girder_worker_run_fails)
        self.route('POST', ('test_girder_worker_run_as_celery_task',),
                   self.test_traditional_girder_worker_run_as_celery_task)
        self.route('POST', ('test_girder_worker_run_as_celery_task_fails',),
                   self.test_traditional_girder_worker_run_as_celery_task_fails)
        self.route('POST', ('test_task_cancel', ),
                   self.test_traditional_task_cancel)
        self.route('POST', ('test_task_cancel_in_queue', ),
                   self.test_traditional_task_cancel_in_queue)

        self.girder_worker_run_analysis = {
            'name': 'add',
            'inputs': [
                {'name': 'a', 'type': 'integer', 'format': 'integer', 'default':
                 {'format': 'json', 'data': '0'}},
                {'name': 'b', 'type': 'integer', 'format': 'integer'}
            ],
            'outputs': [{'name': 'c', 'type': 'integer', 'format': 'integer'}],
            'script': 'c = a + b',
            'mode': 'python'}

        self.girder_worker_run_failing_analysis = copy.copy(self.girder_worker_run_analysis)
        self.girder_worker_run_failing_analysis['script'] = 'this should fail'

        self.girder_worker_run_inputs = {'a': {'format': 'integer', 'data': 1},
                                         'b': {'format': 'integer', 'data': 2}}

        self.girder_worker_run_outputs = {'c': {'format': 'integer'}}

        self.girder_worker_run_cancelable = {
            'name': 'cancelable',
            'inputs': [
            ],
            'outputs': [],
            'script': 'import time\n'
                      'count = 0\n' +
                      'while not _celery_task.canceled and count < 20:\n' +
                      '  time.sleep(1)\n' +
                      '  count += 1\n',
            'mode': 'python'}

    # Traditional endpoints

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test traditional job creation with custom task'))
    def test_traditional_job_custom_task_name(self, params):
        number = 20

        jobModel = self.model('job', 'jobs')

        job = jobModel.createJob(
            title='test_traditional_job_custom_task_name',
            type='traditional', handler='worker_handler',
            user=self.getCurrentUser(), public=False, args=(number,), kwargs={},
            otherFields={
                'celeryTaskName': 'common_tasks.test_tasks.fib.fibonacci'
            })

        job['kwargs']['jobInfo'] = utils.jobInfoSpec(job)

        jobModel.save(job)
        jobModel.scheduleJob(job)

        return job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test traditional job creation with custom task fails correctly'))
    def test_traditional_job_custom_task_name_fails(self, params):
        jobModel = self.model('job', 'jobs')

        job = jobModel.createJob(
            title='test_traditional_job_custom_task_name_fails',
            type='traditional', handler='worker_handler',
            user=self.getCurrentUser(), public=False, args=(), kwargs={},
            otherFields={
                'celeryTaskName': 'common_tasks.test_tasks.fail.fail_after'
            })

        job['kwargs']['jobInfo'] = utils.jobInfoSpec(job)

        jobModel.save(job)
        jobModel.scheduleJob(job)

        return job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test running a celery task from a girder_worker.run job'))
    def test_traditional_job_girder_worker_run(self, params):

        jobModel = self.model('job', 'jobs')
        job = jobModel.createJob(
            title='test_traditional_job_girder_worker_run',
            type='traditional', handler='worker_handler',
            user=self.getCurrentUser(), public=False, args=(self.girder_worker_run_analysis,),
            kwargs={'inputs': self.girder_worker_run_inputs,
                    'outputs': self.girder_worker_run_outputs})

        job['kwargs']['jobInfo'] = utils.jobInfoSpec(job)

        jobModel.save(job)
        jobModel.scheduleJob(job)

        return job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test running a celery task from a girder_worker.run job fails correctly'))
    def test_traditional_job_girder_worker_run_fails(self, params):

        jobModel = self.model('job', 'jobs')
        job = jobModel.createJob(
            title='test_traditional_job_girder_worker_run_fails',
            type='traditional', handler='worker_handler',
            user=self.getCurrentUser(), public=False,
            args=(self.girder_worker_run_failing_analysis,),
            kwargs={'inputs': self.girder_worker_run_inputs,
                    'outputs': self.girder_worker_run_outputs})

        job['kwargs']['jobInfo'] = utils.jobInfoSpec(job)

        jobModel.save(job)
        jobModel.scheduleJob(job)

        return job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test running girder_worker.run as a celery task'))
    def test_traditional_girder_worker_run_as_celery_task(self, params):
        from girder_worker.tasks import run as girder_worker_run

        analysis = {
            'name': 'add',
            'inputs': [
                {
                    'name': 'a',
                    'type': 'integer',
                    'format': 'integer',
                    'default': {
                        'format': 'json',
                        'data': '0'
                    }
                },
                {
                    'name': 'b',
                    'type': 'integer',
                    'format': 'integer'
                }
            ],
            'outputs': [{'name': 'c', 'type': 'integer', 'format': 'integer'}],
            'script': 'c = a + b',
            'mode': 'python'}

        inputs = {'a': {'format': 'integer', 'data': 1},
                  'b': {'format': 'integer', 'data': 2}}

        outputs = {'c': {'format': 'integer'}}

        girder_worker_run._girder_job_title = 'test_traditional_girder_worker_run_as_celery_task'
        a = girder_worker_run.delay(analysis, inputs=inputs, outputs=outputs)

        return a.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test running girder_worker.run as a celery task fails_correctly'))
    def test_traditional_girder_worker_run_as_celery_task_fails(self, params):
        from girder_worker.tasks import run as girder_worker_run

        analysis = {
            'name': 'add',
            'inputs': [
                {
                    'name': 'a',
                    'type': 'integer',
                    'format': 'integer',
                    'default': {
                        'format': 'json',
                        'data': '0'
                    }
                },
                {
                    'name': 'b',
                    'type': 'integer',
                    'format': 'integer'
                }
            ],
            'outputs': [{'name': 'c', 'type': 'integer', 'format': 'integer'}],
            'script': 'this should fail',
            'mode': 'python'}

        inputs = {'a': {'format': 'integer', 'data': 1},
                  'b': {'format': 'integer', 'data': 2}}

        outputs = {'c': {'format': 'integer'}}

        girder_worker_run._girder_job_title = \
            'test_traditional_girder_worker_run_as_celery_task_fails'

        a = girder_worker_run.delay(analysis, inputs=inputs, outputs=outputs)

        return a.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test canceling a running task'))
    def test_traditional_task_cancel(self, params):
        jobModel = self.model('job', 'jobs')
        job = jobModel.createJob(
            title='test_traditional_task_cancel',
            type='worker', handler='worker_handler',
            user=self.getCurrentUser(), public=False, args=(self.girder_worker_run_cancelable,),
            kwargs={'inputs': {},
                    'outputs': {}})

        job['kwargs']['jobInfo'] = utils.jobInfoSpec(job)

        jobModel.save(job)
        jobModel.scheduleJob(job)
        assert wait_for_status(self.getCurrentUser(), job, JobStatus.RUNNING)
        jobModel.cancelJob(job)

        return job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test canceling a queued task'))
    def test_traditional_task_cancel_in_queue(self, params):
        # Fill up queue
        blockers = []
        for _ in range(0, multiprocessing.cpu_count()):
            blockers .append(cancelable.delay(sleep_interval=0.1))

        jobModel = self.model('job', 'jobs')
        job = jobModel.createJob(
            title='test_traditional_task_cancel',
            type='worker', handler='worker_handler',
            user=self.getCurrentUser(), public=False, args=(self.girder_worker_run_cancelable,),
            kwargs={'inputs': {},
                    'outputs': {}})

        job['kwargs']['jobInfo'] = utils.jobInfoSpec(job)

        jobModel.save(job)
        jobModel.scheduleJob(job)
        jobModel.cancelJob(job)

        # Now clean up the blockers
        for blocker in blockers:
            blocker.revoke()

        return job
