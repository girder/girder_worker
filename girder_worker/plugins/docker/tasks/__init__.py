import sys
import docker
from docker.errors import DockerException
from requests.exceptions import ReadTimeout

from girder_worker.app import app
from girder_worker import logger
from girder_worker.core import utils
from girder_worker.plugins.docker.stream_adapter import DockerStreamPushAdapter
from girder_worker.plugins.docker import nvidia


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


def _run_container(image, container_args, **kwargs):
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


def _run_select_loop(task, container, output_pipes, input_pipes):
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

        def close_output(output):
            return output not in (stdout.fileno(), stderr.fileno())

        output_pipes[stdout.fileno()] = DockerStreamPushAdapter(output_pipes.get(
            '_stdout', utils.WritePipeAdapter({}, sys.stdout)))
        output_pipes[stderr.fileno()] = DockerStreamPushAdapter(output_pipes.get(
            '_stderr', utils.WritePipeAdapter({}, sys.stderr)))

        # Run select loop
        utils.select_loop(exit_condition=exit_condition, close_output=close_output,
                          outputs=output_pipes, inputs=input_pipes)

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


def _docker_run(task, image, pull_image=True, entrypoint=None, container_args=None,
                volumes={}, remove_container=False, output_pipes={}, input_pipes={},
                **kwargs):

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

    container = _run_container(image, container_args, **run_kwargs)
    try:
        _run_select_loop(task, container, output_pipes, input_pipes)
    finally:
        if container and remove_container:
            container.remove()


@app.task(bind=True)
def docker_run(task, image, pull_image=True, entrypoint=None, container_args=None,
               volumes={}, remove_container=False, output_pipes={}, input_pipes={},
               **kwargs):
    return _docker_run(
        task, image, pull_image, entrypoint, container_args, volumes,
        remove_container, output_pipes, input_pipes, **kwargs)
