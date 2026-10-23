from unittest import mock

import pytest

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


@pytest.mark.parametrize('canceled', [True, False])
def test__docker_run_canceled_skips_result_hooks(canceled):
    def select_loop(task, *args):
        # the select loop checks for a cancel while the container runs
        task.canceled

    hook = mock.Mock()
    with mock.patch('girder_worker.task.is_revoked', return_value=canceled), \
            mock.patch('girder_worker.docker.tasks._run_container'), \
            mock.patch('girder_worker.docker.tasks._run_select_loop',
                       side_effect=select_loop):
        docker_run.push_request(girder_result_hooks=[hook])
        try:
            docker_run(image='test', pull_image=False)
        finally:
            docker_run.pop_request()

    # a canceled container never wrote its outputs, so they must not be uploaded
    if canceled:
        hook.transform.assert_not_called()
    else:
        hook.transform.assert_called_once()
    hook.exception.assert_not_called()


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
