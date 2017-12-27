"""
This module is necessary since the docker python library does not yet provide built-in support
for nvidia-docker tooling. If some incarnation of this feature[1] makes its way into a release
of docker-py, this module can go away. Until then, the ideas in that PR have been copied and
lightly modified here.

[1] https://github.com/docker/docker-py/pull/1560
"""

import os
import re
import requests

from docker.api.client import APIClient
from docker.client import DockerClient
from docker.errors import DockerException
from docker.utils.utils import parse_devices

NVIDIA_DEFAULT_HOST = 'localhost'
NVIDIA_DEFAULT_PORT = 3476


def get_nvidia_docker_endpoint():
    host = os.environ.get('NV_HOST', 'http://%s:%s' % (NVIDIA_DEFAULT_HOST, NVIDIA_DEFAULT_PORT))
    return host + '/docker/cli/json'


def get_nvidia_configuration():
    url = get_nvidia_docker_endpoint()
    try:
        return requests.get(url).json()
    except requests.exceptions.ConnectionError:
        url = get_nvidia_docker_endpoint()
        raise NvidiaConnectionError((
            'Couldn\'t connect to nvidia-driver-plugin at {url} - is it running and accessible?.\n'
            'Try: "curl {url}" or "systemctl start nvidia-docker"').format(url=url), url)


def is_nvidia_image(api, image):
    labels = api.inspect_image(image).get('Config', {}).get('Labels')
    return bool(labels and labels.get('com.nvidia.volumes.needed') == 'nvidia_driver')


def add_nvidia_docker_to_config(container_config):
    if not container_config.get('HostConfig', None):
        container_config['HostConfig'] = {}

    nvidia_config = get_nvidia_configuration()

    # Setup the Volumes
    container_config['HostConfig'].setdefault('VolumeDriver', nvidia_config['VolumeDriver'])
    container_config['HostConfig'].setdefault('Binds', [])
    container_config['HostConfig']['Binds'].extend(nvidia_config['Volumes'])

    # Get nvidia control devices
    devices = container_config['HostConfig'].get('Devices', [])
    # suport both '0 1' and '0, 1' formats, just like nvidia-docker
    gpu_isolation = os.getenv('NV_GPU', '').replace(',', ' ').split()
    pattern = re.compile(r'/nvidia([0-9]+)$')
    for device in nvidia_config['Devices']:
        if gpu_isolation:
            card_number = pattern.search(device)
            if card_number and card_number.group(1) not in gpu_isolation:
                continue
        devices.extend(parse_devices([device]))

    container_config['HostConfig']['Devices'] = devices


class NvidiaDockerClient(DockerClient):
    def __init__(self, *args, **kwargs):
        self.api = NvidiaAPIClient(*args, **kwargs)


class NvidiaAPIClient(APIClient):
    def create_container_config(self, image, *args, **kwargs):
        container_config = (
            super(NvidiaAPIClient, self).create_container_config(image, *args, **kwargs))

        if is_nvidia_image(self, image):
            add_nvidia_docker_to_config(container_config)

        return container_config


class NvidiaConnectionError(DockerException):
    def __init__(self, msg, nvidia_url):
        self.msg = msg
        self.url = nvidia_url
