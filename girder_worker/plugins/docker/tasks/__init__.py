import sys
import docker
from docker.errors import DockerException
from requests.exceptions import ReadTimeout

from girder_worker.app import app
from girder_worker import logger
from girder_worker.core import utils
from girder_worker.plugins.docker.stream_adapter import DockerStreamPushAdapter
from girder_worker.plugins.docker import nvidia
from girder_worker.plugins.docker.io import (
    WriteStreamConnector,
    ReadStreamConnector,
    FileDescriptorReader
)
from girder_worker.plugins.docker.tasks.transform import (
    ContainerStdErr,
    ContainerStdOut,
    Connect
)


BLACKLISTED_DOCKER_RUN_ARGS = ['tty', 'detach']


def _pull_image(image):
    """
    Pulls the specified Docker image onto this worker.
    """
    client = docker.from_env(version='auto')
    try:
        client.images.pull(image)
    except DockerException as dex:
        logger.error('Error pulling Docker image %s:' % image)
        logger.exception(dex)
        raise


def _run_container(image, container_args,  **kwargs):
    # TODO we could allow configuration of non default socket
    client = docker.from_env(version='auto')
    if nvidia.is_nvidia_image(client.api, image):
        client = nvidia.NvidiaDockerClient.from_env(version='auto')

    logger.info('Running container: image: %s args: %s kwargs: %s'
                % (image, container_args, kwargs))
    try:
        return client.containers.run(image, container_args, **kwargs)
    except DockerException as dex:
        logger.error(dex)
        raise

def _run_select_loop(task, container, read_stream_connectors, write_stream_connectors):
    stdout = None
    stderr = None
    try:
        # attach to standard streams
        stdout = container.attach_socket(params={
            'stdout': True,
            'logs': True,
            'stream': True
        })

        stderr = container.attach_socket(params={
            'stderr': True,
            'logs': True,
            'stream': True
        })

        def exit_condition():
            container.reload()
            return container.status in ['exited', 'dead'] or task.canceled


        # Look for ContainerStdOut and ContainerStdErr instances that need
        # to be replace with the real container streams.
        stdout_connected = False
        for read_stream_connector in read_stream_connectors:
            if isinstance(read_stream_connector.input, ContainerStdOut):
                stdout_reader = FileDescriptorReader(stdout.fileno())
                read_stream_connector.output = DockerStreamPushAdapter(read_stream_connector.output)
                read_stream_connector.input = stdout_reader
                stdout_connected = True
                break

        stderr_connected = False
        for read_stream_connector in read_stream_connectors:
            if isinstance(read_stream_connector.input, ContainerStdErr):
                stderr_reader = FileDescriptorReader(stderr.fileno())
                read_stream_connector.output = DockerStreamPushAdapter(read_stream_connector.output)
                read_stream_connector.input = stderr_reader
                stderr_connected = True
                break

        # If not stdout and stderr connection has been provided just use
        # sys.stdXXX
        if not stdout_connected:
            stdout_reader = FileDescriptorReader(stdout.fileno())
            connector = ReadStreamConnector(stdout_reader,
                DockerStreamPushAdapter(utils.WritePipeAdapter({}, sys.stdout)))
            read_stream_connectors.append(connector)

        if not stderr_connected:
            stderr_reader = FileDescriptorReader(stderr.fileno())
            connector = ReadStreamConnector(stderr_reader,
                DockerStreamPushAdapter(utils.WritePipeAdapter({}, sys.stderr)))
            read_stream_connectors.append(connector)

        # Run select loop
        utils.select_loop(exit_condition=exit_condition,
                          readers=read_stream_connectors,
                          writers=write_stream_connectors)

        if task.canceled:
            try:
                container.stop()
            # Catch the ReadTimeout from requests and wait for container to
            # exit. See https://github.com/docker/docker-py/issues/1374 for
            # more details.
            except ReadTimeout:
                tries = 10
                while tries > 0:
                    container.reload()
                    if container.status == 'exited':
                        break

                if container.status != 'exited':
                    msg = 'Unable to stop container: %s' % container.id
                    logger.error(msg)
            except DockerException as dex:
                logger.error(dex)
                raise

    finally:
        # Close our stdout and stderr sockets
        if stdout:
            stdout.close()
        if stderr:
            stderr.close()

def _handle_streaming_args(args):
    processed_arg = []
    write_streams = []
    read_streams = []
    for arg in args:
        # TODO eventually this will be done automagically
        if isinstance(arg, Connect):
            connector = arg.transform()
            if isinstance(connector, WriteStreamConnector):
                write_streams.append(connector)
            else:
                read_streams.append(connector)

            # Get any container argument associated with this stream
            arg = connector.container_arg()

        processed_arg.append(arg)

    return (processed_arg, read_streams, write_streams)


def _docker_run(task, image, pull_image=True, entrypoint=None, container_args=None,
                volumes={}, remove_container=False, stream_connectors=[], **kwargs):

    if pull_image:
        logger.info('Pulling Docker image: %s', image)
        _pull_image(image)

    if entrypoint is not None:
        if not isinstance(entrypoint, (list, tuple)):
            entrypoint = [entrypoint]

    run_kwargs = {
        'tty': False,
        'volumes': volumes,
        'detach': True
    }

    # Allow run args to overridden,filter out any we don't want to override
    extra_run_kwargs = {k: v for k, v in kwargs.items() if k not
                        in BLACKLISTED_DOCKER_RUN_ARGS}
    run_kwargs.update(extra_run_kwargs)

    if entrypoint is not None:
        run_kwargs['entrypoint'] = entrypoint

    (container_args, read_streams, write_streams) = \
        _handle_streaming_args(container_args)

    for connector in stream_connectors:
        if isinstance(connector, ReadStreamConnector):
            read_streams.append(connector)
        elif isinstance(connector, WriteStreamConnector):
            write_streams.append(connector)

    # We need to open any read streams before starting the container, so the
    # underling named pipes are opened for read.
    for stream in read_streams:
        stream.open()

    container = _run_container(image, container_args, **run_kwargs)
    try:
        _run_select_loop(task, container, read_streams, write_streams)
    finally:
        if container and remove_container:
            container.remove()


@app.task(bind=True)
def docker_run(task, image, pull_image=True, entrypoint=None, container_args=None,
               volumes={}, remove_container=False, stream_connectors=[], **kwargs):
    return _docker_run(
        task, image, pull_image, entrypoint, container_args, volumes,
        remove_container, stream_connectors, **kwargs)
