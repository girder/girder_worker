import os

from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, filtermodel
from girder.utility.model_importer import ModelImporter

from girder.plugins.worker import utils
from girder.plugins.worker.constants import PluginSettings
from girder_worker.docker.tasks import docker_run

from girder_worker.docker.transform import (
    StdOut,
    NamedOutputPipe,
    NamedInputPipe,
    Connect,
    GirderFileToStream
)

TEST_IMAGE = 'girder/girder_worker_test:latest'


class DockerTestEndpoints(Resource):
    def __init__(self):
        super(DockerTestEndpoints, self).__init__()
        self.route('POST', ('test_docker_run', ),
                   self.test_docker_run)
        self.route('POST', ('test_docker_run_mount_volume', ),
                   self.test_docker_run_mount_volume)
        self.route('POST', ('test_docker_run_named_pipe_output', ),
                   self.test_docker_run_named_pipe_output)
        self.route('POST', ('test_docker_run_girder_file_to_named_pipe', ),
                   self.test_docker_run_girder_file_to_named_pipe)

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test basic docker_run.'))
    def test_docker_run(self, params):
        result = docker_run.delay(TEST_IMAGE, pull_image=True, container_args=['stdio', '-m', 'hello docker!'],
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
<<<<<<< HEAD
        result = docker_run.delay(TEST_IMAGE, pull_image=True, container_args=['volume', mount_path],
=======
        result = docker_run.delay(TEST_IMAGE, pull_image=True, container_args=['volume', '-p', mount_path],
>>>>>>> 222dd08... Refactor test script to use click
            remove_container=True, volumes=volumes)

        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test mounting a volume.'))
    def test_docker_run_named_pipe_output(self, params):
        tmp_dir = params.get('tmpDir')
        mount_dir = '/mnt/girder_worker/data'
        pipe_name = 'output_pipe'

        volumes = {
            tmp_dir: {
                'bind': mount_dir,
                'mode': 'rw'
            }
        }

        inside_path = os.path.join(mount_dir, pipe_name)
        outside_path = os.path.join(tmp_dir, pipe_name)

        connect = Connect(NamedOutputPipe(inside_path, outside_path), StdOut())

        result = docker_run.delay(TEST_IMAGE, pull_image=True, container_args=['output_pipe', '-p', connect],
            remove_container=True, volumes=volumes)

        return result.job


    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test mounting a volume.'))
    def test_docker_run_girder_file_to_named_pipe(self, params):
        tmp_dir = params.get('tmpDir')
        file_id = params.get('fileId')
        mount_dir = '/mnt/girder_worker/data'
        pipe_name = 'input_pipe'

        volumes = {
            tmp_dir: {
                'bind': mount_dir,
                'mode': 'rw'
            }
        }

        inside_path = os.path.join(mount_dir, pipe_name)
        outside_path = os.path.join(tmp_dir, pipe_name)

        connect = Connect(GirderFileToStream(file_id), NamedInputPipe(inside_path, outside_path))

        result = docker_run.delay(TEST_IMAGE, pull_image=True, container_args=['input_pipe', connect],
            remove_container=True, volumes=volumes)


        return result.job
