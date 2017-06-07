from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource
from common_tasks.test_tasks.fib import fibonacci
from girder_worker.app import app

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

    info['apiRoot'].integration_tests = IntegrationTestEndpoints()
