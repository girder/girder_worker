import copy
from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, filtermodel, Prefix
from girder.utility.model_importer import ModelImporter

from girder.plugins.worker import utils
from girder.plugins.worker.constants import PluginSettings

from girder_worker.app import app
from celery.exceptions import TimeoutError
import multiprocessing
from girder_worker.utils import JobStatus
from .raw import CeleryTestEndpoints
from .traditional import TraditionalTestEndpoints


class CommonTestEndpoints(Resource):
    def __init__(self):
        super(CommonTestEndpoints, self).__init__()

        # POST because get_result is not idempotent.
        self.route('POST', ('result', ), self.get_result)

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

def load(info):
    # Note: Some endpoints rely on the celery application defined in
    # the worker plugin rather than the one defined in
    # girder_worker. This means we need to make sure the
    # backend/broker are set to the rabbitmq docker container
    settings = ModelImporter.model('setting')
    settings.set(PluginSettings.BACKEND, 'amqp://guest:guest@rabbit/')
    settings.set(PluginSettings.BROKER, 'amqp://guest:guest@rabbit/')

    info['apiRoot'].integration_tests = Prefix()
    info['apiRoot'].integration_tests.common = CommonTestEndpoints()
    info['apiRoot'].integration_tests.celery = CeleryTestEndpoints()
    info['apiRoot'].integration_tests.traditional = TraditionalTestEndpoints()
