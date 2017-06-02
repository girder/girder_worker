from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource
from common_tasks.test_tasks.fib import fibonacci


class IntegrationTestEndpoints(Resource):
    def __init__(self):
        super(IntegrationTestEndpoints, self).__init__()
        self.resourceName = 'integration_tests'

        # Automatically add routes for any endpoint
        # that begins with 'test_'
        for attr in dir(self):
            if attr.startswith('test_'):
                endpoint = getattr(self, attr)
                if hasattr(endpoint, '__call__'):
                    self.route('POST', (attr, ), endpoint)

    @access.token
    @describeRoute(
        Description('Test celery task delay'))
    def test_celery_task_delay(self, params):
        result = fibonacci.delay(20)
        return result.job


def load(info):
    info['apiRoot'].integration_tests = IntegrationTestEndpoints()
