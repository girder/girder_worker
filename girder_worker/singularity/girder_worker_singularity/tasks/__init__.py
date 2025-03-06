import os
import shutil

from girder_worker import logger
from girder_worker.docker.io import (FDReadStreamConnector,
                                     FDWriteStreamConnector)
from girder_worker.docker.tasks import _handle_streaming_args, DockerTask


BLACKLISTED_DOCKER_RUN_ARGS = ['tty', 'detach']

class SingularityTask(DockerTask):
    def _cleanup_temp_volumes(self, temp_volumes, default_temp_volume):
        temp_volumes = [v.host_path for v in temp_volumes if os.path.exists(v.host_path)]
        if default_temp_volume._transformed:
            temp_volumes.append(default_temp_volume.host_path)

        for v in temp_volumes:
            shutil.rmtree(v)


def singularity_run(task, **kwargs):
    volumes = kwargs.pop('volumes', {})
    container_args = kwargs.pop('container_args', [])
    stream_connectors = kwargs['stream_connectors'] or []
    image = kwargs.get('image') or ''
    entrypoint = None
    if not image:
        logger.exception('Image name cannot be empty')
        raise Exception('Image name cannot be empty')

    run_kwargs = {
        'tty': False,
        'volumes': volumes
    }

    # Allow run args to be overridden,filter out any we don't want to override
    extra_run_kwargs = {k: v for k, v in kwargs.items() if k not in BLACKLISTED_DOCKER_RUN_ARGS}
    run_kwargs.update(extra_run_kwargs)

    # Make entrypoint as pwd
    # TODO: this doesn't do anything
    if entrypoint is not None:
        run_kwargs['entrypoint'] = entrypoint

    log_file_name = kwargs['log_file']

    container_args, read_streams, write_streams = _handle_streaming_args(container_args)
    # MODIFIED FOR SINGULARITY (CHANGE CODE OF SINGULARITY CONTAINER)
    for connector in stream_connectors:
        if isinstance(connector, FDReadStreamConnector):
            read_streams.append(connector)
        elif isinstance(connector, FDWriteStreamConnector):
            write_streams.append(connector)
        else:
            raise TypeError(
                "Expected 'FDReadStreamConnector' or 'FDWriterStreamConnector', received '%s'"
                % type(connector))

    from girder_worker_slurm import slurm_dispatch
    slurm_dispatch(task, container_args, run_kwargs, read_streams, write_streams, log_file_name)

    results = []
    if hasattr(task.request, 'girder_result_hooks'):
        results = (None,) * len(task.request.girder_result_hooks)

    return results
