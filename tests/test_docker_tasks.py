import pytest
import mock
from girder_worker.docker.transforms.girder import GirderFolderIdToVolume, GirderFileIdToVolume
from girder_worker.docker.tasks import ( # noqa F401
    DockerTask,
    _docker_run,
    _handle_streaming_args,
    _pull_image,
    _run_container,
    _run_select_loop,
    docker_run
)


# TODO: test DockerTask
@pytest.mark.skip
def test_DockerTask():
    pass


# TODO: test _docker_run
@pytest.mark.skip
def test__docker_run():
    pass


# TODO: test _handle_streaming_args
@pytest.mark.skip
def test__handle_streaming_args():
    pass


# TODO: test _pull_image
@pytest.mark.skip
def test__pull_image():
    pass


# TODO: test _run_container
@pytest.mark.skip
def test__run_container():
    pass


# TODO: test _run_select_loop
@pytest.mark.skip
def test__run_select_loop():
    pass


# TODO: test docker_run
@pytest.mark.skip
def test_docker_run():
    pass


@pytest.fixture
def patch_select_loop():
    with mock.patch('girder_worker.docker.tasks.utils.select_loop') as m:
        yield m


@pytest.fixture
def patch_task_canceled():
    with mock.patch('girder_worker.task.is_revoked', return_value=False) as m:
        yield m


@pytest.fixture
def patch_docker_client_containers_run():
    with mock.patch('girder_worker.docker.tasks.docker.from_env',
                    return_value=mock.MagicMock(name='client')) as from_env:
        client = from_env.return_value
        client.containers.run.return_value.attrs = {
            'State': {'ExitCode': 0}
        }
        yield client.containers.run


def test_docker_run_folder_name_with_spaces(
        mock_gc,
        patch_makedirs,
        patch_select_loop,
        patch_task_canceled,
        patch_docker_client_containers_run):

    output_path = '/tmp/foo/bar'
    docker_run('bogus_image', container_args=[
        GirderFolderIdToVolume('BOGUS_FOLDER_ID', folder_name='Folder Name', gc=mock_gc),
        GirderFileIdToVolume('BOGUS_FILE_ID', gc=mock_gc), '--someoption', output_path
    ], pull_image=False, runtime='nvidia')

    assert patch_docker_client_containers_run.call_count >= 1
    args = patch_docker_client_containers_run.call_args_list[0][0]

    # args should be of the form:
    # ('bogus_image',
    #  ['/mnt/girder_worker/afdc8ca5e6524821980cd3a88f655bbe/BOGUS_FOLDER_ID/Folder Name',
    #   '/mnt/girder_worker/afdc8ca5e6524821980cd3a88f655bbe/BOGUS_FILE_ID/bogus.txt'])

    assert args[0] == 'bogus_image'
    assert len(args[1]) == 4
    assert args[1][0].endswith('BOGUS_FOLDER_ID/Folder Name')
    assert args[1][1].endswith('BOGUS_FILE_ID/bogus.txt')
