from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource


class IntegrationTestEndpoints(Resource):
    def __init__(self):
        super(IntegrationTestEndpoints, self).__init__()
        self.resourceName = 'integration_tests'

        self.route('POST', ('test', ), self.test)

    @access.token
    @describeRoute(
        Description('Get an asyn result')
    )
    def test(self, params):
        return 'SUCCESS'


def load(info):
    info['apiRoot'].integration_tests = IntegrationTestEndpoints()
