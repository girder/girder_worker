import os
import pytest
import mock
import requests

from girder_worker.docker.nvidia import (
    NVIDIA_DEFAULT_HOST,
    NVIDIA_DEFAULT_PORT,
    NvidiaAPIClient,
    NvidiaConnectionError,
    get_nvidia_docker_endpoint,
    get_nvidia_configuration,
    is_nvidia_image
)


def test_nvidia_docker_endpoint_returns_defaults():
    assert get_nvidia_docker_endpoint() == \
        'http://{}:{}/docker/cli/json'.format(NVIDIA_DEFAULT_HOST, NVIDIA_DEFAULT_PORT)


def test_docker_endpoint_responds_to_NV_HOST(monkeypatch):
    monkeypatch.setitem(os.environ, 'NV_HOST', 'http://bogus.com:8888')
    assert get_nvidia_docker_endpoint() == 'http://bogus.com:8888/docker/cli/json'


def test_get_nvidia_configuration_calls_docker_endpoint_url():
    with mock.patch('girder_worker.docker.nvidia.requests.get') as m:
        get_nvidia_configuration()
        m.assert_called_with(get_nvidia_docker_endpoint())


def test_get_nvidia_configuration_raises_NvidiaConnectionError_on_requests_ConnectionError():
    with mock.patch('girder_worker.docker.nvidia.requests.get') as m:
        m.side_effect = requests.exceptions.ConnectionError()
        with pytest.raises(NvidiaConnectionError):
            get_nvidia_configuration()


def test_is_nvidia_image_no_labels_returns_false():
    api = mock.MagicMock(spec=NvidiaAPIClient)
    api.inspect_image.return_value = {}
    assert is_nvidia_image(api, 'bogus/image:latest') is False


def test_is_nvidia_image_no_nvidia_labels_returns_false():
    api = mock.MagicMock(spec=NvidiaAPIClient)
    api.inspect_image.return_value = {'Config': {'Labels': {'some': 'label'}}}
    assert is_nvidia_image(api, 'bogus/image:latest') is False


def test_is_nvidia_image_returns_true():
    api = mock.MagicMock(spec=NvidiaAPIClient)
    api.inspect_image.return_value = {'Config':
                                      {'Labels':
                                       {'com.nvidia.volumes.needed': 'nvidia_driver'}}}
    assert is_nvidia_image(api, 'bogus/image:latest') is True


def test_NvidiaAPIClient_create_container_config_is_nvidia_image_calls_add_nvidia_docker():
    with mock.patch('girder_worker.docker.nvidia.APIClient.create_container_config'):
        with mock.patch('girder_worker.docker.nvidia.is_nvidia_image', return_value=True):
            with mock.patch('girder_worker.docker.nvidia.add_nvidia_docker_to_config') as m:
                api = NvidiaAPIClient()
                api.create_container_config('bogus/image:latest')
                m.assert_called_once()


def test_NvidiaAPIClient_create_container_config_is_nvidia_image_does_not_call_add_nvidia_docker():
    with mock.patch('girder_worker.docker.nvidia.APIClient.create_container_config'):
        with mock.patch('girder_worker.docker.nvidia.is_nvidia_image', return_value=False):
            with mock.patch('girder_worker.docker.nvidia.add_nvidia_docker_to_config') as m:
                api = NvidiaAPIClient()
                api.create_container_config('bogus/image:latest')
                m.assert_not_called()


# TODO: add_nvidia_docker_to_config
