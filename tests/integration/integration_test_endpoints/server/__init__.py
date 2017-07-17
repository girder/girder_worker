import copy
from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, filtermodel
from girder.utility.model_importer import ModelImporter

from girder.plugins.worker import utils
from girder.plugins.worker.constants import PluginSettings

from common_tasks.test_tasks.fib import fibonacci
from common_tasks.test_tasks.fail import fail_after
from common_tasks.test_tasks.girder_client import request_private_path

from girder_worker.app import app
from celery.exceptions import TimeoutError


class IntegrationTestEndpoints(Resource):
    def __init__(self):
        super(IntegrationTestEndpoints, self).__init__()
        self.resourceName = 'integration_tests'

        # POST because get_result is not idempotent.
        self.route('POST', ('result', ), self.get_result)

        self.route('POST', ('celery', 'test_task_delay', ),
                   self.test_celery_task_delay)
        self.route('POST', ('celery', 'test_task_delay_fails', ),
                   self.test_celery_task_delay_fails)
        self.route('POST', ('celery', 'test_task_apply_async', ),
                   self.test_celery_task_apply_async)
        self.route('POST', ('celery', 'test_task_apply_async_fails', ),
                   self.test_celery_task_apply_async_fails)
        self.route('POST', ('celery', 'test_task_signature_delay', ),
                   self.test_celery_task_signature_delay)
        self.route('POST', ('celery', 'test_task_signature_delay_fails', ),
                   self.test_celery_task_signature_delay_fails)
        self.route('POST', ('celery', 'test_task_signature_apply_async', ),
                   self.test_celery_task_signature_apply_async)
        self.route('POST', ('celery', 'test_task_signature_apply_async_fails', ),
                   self.test_celery_task_signature_apply_async_fails)

        self.route('POST', ('celery', 'test_task_delay_with_custom_job_options', ),
                   self.test_celery_task_delay_with_custom_job_options)
        self.route('POST', ('celery', 'test_task_apply_async_with_custom_job_options', ),
                   self.test_celery_task_apply_async_with_custom_job_options)

        self.route('POST', ('celery', 'test_girder_client_generation', ),
                   self.test_celery_girder_client_generation)
        self.route('POST', ('celery', 'test_girder_client_bad_token_fails', ),
                   self.test_celery_girder_client_bad_token_fails)

        self.route('POST', ('traditional', 'test_job_girder_worker_run'),
                   self.test_traditional_job_girder_worker_run)
        self.route('POST', ('traditional', 'test_job_custom_task_name'),
                   self.test_traditional_job_custom_task_name)
        self.route('POST', ('traditional', 'test_job_custom_task_name_fails'),
                   self.test_traditional_job_custom_task_name_fails)
        self.route('POST', ('traditional', 'test_job_girder_worker_run_fails'),
                   self.test_traditional_job_girder_worker_run_fails)
        self.route('POST', ('traditional', 'test_girder_worker_run_as_celery_task'),
                   self.test_traditional_girder_worker_run_as_celery_task)
        self.route('POST', ('traditional', 'test_girder_worker_run_as_celery_task_fails'),
                   self.test_traditional_girder_worker_run_as_celery_task_fails)

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

    @access.token
    @describeRoute(
        Description('Utility endpoint to get an async result from a celery id')
        .param('celery_id', 'celery async ID', dataType='string'))
    def get_result(self, params):
        cid = params['celery_id']
        a1 = app.AsyncResult(cid)

        # Note: There is no reasonable way to validate a celery task
        # asyncresult id. See:
        # https://github.com/celery/celery/issues/3596#issuecomment-262102185
        # This means for ALL values of celery_id return either the
        # value or None. Note also that you will only be able to get
        # the result via this method once. All subsequent calls will
        # return None.
        try:
            return a1.get(timeout=0.2)
        except TimeoutError:
            return None

    # Testing custom job option API for celery tasks

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task delay with custom job options'))
    def test_celery_task_delay_with_custom_job_options(self, params):
        result = fibonacci.delay(20, girder_job_title='TEST DELAY TITLE')
        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task apply_async with custom job options'))
    def test_celery_task_apply_async_with_custom_job_options(self, params):
        result = fibonacci.apply_async((20,), {}, girder_job_title='TEST APPLY_ASYNC TITLE')
        return result.job

    # Testing basic celery API

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task delay'))
    def test_celery_task_delay(self, params):
        result = fibonacci.delay(20)
        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task delay fails correctly'))
    def test_celery_task_delay_fails(self, params):
        result = fail_after.delay()
        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task apply_async'))
    def test_celery_task_apply_async(self, params):
        result = fibonacci.apply_async((20,))
        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task apply_async fails correctly'))
    def test_celery_task_apply_async_fails(self, params):
        result = fail_after.apply_async((0.5,))
        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task signature delay'))
    def test_celery_task_signature_delay(self, params):
        signature = fibonacci.s(20)
        result = signature.delay()
        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task signature delay fails correctly'))
    def test_celery_task_signature_delay_fails(self, params):
        signature = fail_after.s(0.5)
        result = signature.delay()
        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task apply_async'))
    def test_celery_task_signature_apply_async(self, params):
        signature = fibonacci.s(20)
        result = signature.apply_async()
        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test celery task apply_async fails correctly'))
    def test_celery_task_signature_apply_async_fails(self, params):
        signature = fail_after.s(0.5)
        result = signature.apply_async()
        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test girder client is generated and can request scoped endpoints'))
    def test_celery_girder_client_generation(self, params):
        token = ModelImporter.model('token').createToken(
            user=self.getCurrentUser())

        result = request_private_path.delay(
            'admin', girder_client_token=str(token['_id']))

        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test girder client with no token can\'t access protected resources'))
    def test_celery_girder_client_bad_token_fails(self, params):
        result = request_private_path.delay('admin', girder_client_token='')

        return result.job

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


def load(info):
    # Note: Some endpoints rely on the celery application defined in
    # the worker plugin rather than the one defined in
    # girder_worker. This means we need to make sure the
    # backend/broker are set to the rabbitmq docker container
    settings = ModelImporter.model('setting')
    settings.set(PluginSettings.BACKEND, 'amqp://guest:guest@rabbit/')
    settings.set(PluginSettings.BROKER, 'amqp://guest:guest@rabbit/')

    info['apiRoot'].integration_tests = IntegrationTestEndpoints()
