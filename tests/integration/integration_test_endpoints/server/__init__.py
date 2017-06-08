from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, filtermodel
from girder.utility.model_importer import ModelImporter

from girder.plugins.worker import utils
from girder.plugins.worker.constants import PluginSettings

from common_tasks.test_tasks.fib import fibonacci
from girder_worker.app import app
from celery.exceptions import TimeoutError

class IntegrationTestEndpoints(Resource):
    def __init__(self):
        super(IntegrationTestEndpoints, self).__init__()
        self.resourceName = 'integration_tests'

        # POST because get_result is not idempotent.
        self.route('POST', ('result', ), self.get_result)

        self.route('POST', ('test_celery_task_delay', ), self.test_celery_task_delay)
        self.route('POST', ('test_traditional_job_custom_task_name', ),
                   self.test_traditional_job_custom_task_name)


    @access.token
    @describeRoute(
        Description('Utility endpoint to get an asyn result from a celery id')
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
        Description('Test traditional job creation with custom task'))
    def test_traditional_job_custom_task_name(self, params):
        number = 20

        jobModel = self.model('job', 'jobs')

        job = jobModel.createJob(
            title='test_traditional_job_custom_task_name',
            type='worker', handler='worker_handler',
            user=self.getCurrentUser(), public=False, args=(number,), kwargs={},
            otherFields={
                'celeryTaskName': 'common_tasks.test_tasks.fib.fibonacci'
            })

        job['kwargs']['jobInfo'] = utils.jobInfoSpec(job)

        jobModel.save(job)
        jobModel.scheduleJob(job)

        return job

def load(info):

    # Note: within the context of the executing docker test
    # environment the RabbitMQ server is addressable as 'rabbit.'
    # Usually we statically configure the broker url in
    # worker.local.cfg or fall back to worker.dist.cfg.  In this case
    # however we are mounting the local girder_worker checkout inside
    # the docker containers and don't want to surprise users by
    # programatically modifying their configuration from the docker
    # container's entrypoint. To solve this we set the broker URL for
    # the girder_worker app inside the girder container here.

    app.conf.update({
        'broker_url': 'amqp://guest:guest@rabbit/'
    })

    # Note: Some endpoints rely on the celery application defined in
    # the worker plugin rather than the one defined in
    # girder_worker. This means we need to make sure the
    # backend/broker are set to the rabbitmq docker container
    settings = ModelImporter.model('setting')
    settings.set(PluginSettings.BACKEND, 'amqp://guest:guest@rabbit/')
    settings.set(PluginSettings.BROKER, 'amqp://guest:guest@rabbit/')

    info['apiRoot'].integration_tests = IntegrationTestEndpoints()
