import os

from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, filtermodel
from girder.utility.model_importer import ModelImporter

from girder.plugins.worker import utils
from girder.plugins.worker.constants import PluginSettings
from girder_worker.docker.tasks import docker_run

TEST_IMAGE = 'girder/girder_worker_test:latest'


class DockerTestEndpoints(Resource):
    def __init__(self):
        super(DockerTestEndpoints, self).__init__()
        self.route('POST', ('test_docker_run', ),
                   self.test_docker_run)
        self.route('POST', ('test_docker_run_mount_volume', ),
                   self.test_docker_run_mount_volume)

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test basic docker_run.'))
    def test_docker_run(self, params):
        result = docker_run.delay(TEST_IMAGE, pull_image=True, container_args=['stdio', 'hello docker!'],
            remove_container=True)

        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test mounting a volume.'))
    def test_docker_run_mount_volume(self, params):
        fixture_dir = params.get('fixtureDir')
        filename = 'read.txt'
        mount_dir = '/mnt/test'
        mount_path = os.path.join(mount_dir, filename)
        volumes = {
            fixture_dir: {
                'bind': mount_dir,
                'mode': 'ro'
            }
        }
        result = docker_run.delay(TEST_IMAGE, pull_image=True, container_args=['volume', mount_path],
            remove_container=True, volumes=volumes)

        return result.job
