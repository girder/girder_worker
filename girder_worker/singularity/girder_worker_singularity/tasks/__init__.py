import os
import threading

from girder_worker_utils import _walk_obj

from girder_worker import logger
from girder_worker.app import Task
from girder_worker.docker.io import (FDReadStreamConnector,
                                     FDWriteStreamConnector)
from girder_worker.docker.tasks import (_handle_streaming_args,
                                        _RequestDefaultTemporaryVolume)
from girder_worker.docker.transforms import TemporaryVolume

from .utils import remove_tmp_folder_apptainer

BLACKLISTED_DOCKER_RUN_ARGS = ['tty', 'detach']

#TODO: this is identical to DockerTask except for _cleanup_temp_volumes. refactor/inherit
# Class for SingularityTask similar to DockerTask
class SingularityTask(Task):
    def _maybe_transform_argument(self, arg):
        return super()._maybe_transform_argument(
            arg, task=self, _default_temp_volume=self.request._default_temp_volume)

    def _maybe_transform_result(self, idx, result):
        return super()._maybe_transform_result(
            idx, result, _default_temp_volume=self.request._default_temp_volume)

    def __call__(self, *args, **kwargs):
        default_temp_volume = _RequestDefaultTemporaryVolume()
        self.request._default_temp_volume = default_temp_volume

        volumes = kwargs.setdefault('volumes', {})
        # If we have a list of volumes, the user provide a list of Volume objects,
        # we need to transform them.
        temp_volumes = []
        if isinstance(volumes, list):
            # See if we have been passed any TemporaryVolume instances.
            for v in volumes:
                if isinstance(v, TemporaryVolume):
                    temp_volumes.append(v)

            # First call the transform method, this we replace default temp volumes
            # with the instance associated with this task create above. That is any
            # reference to TemporaryVolume.default
            _walk_obj(volumes, self._maybe_transform_argument)

            # Now convert them to JSON
            def _json(volume):
                return volume._repr_json_()

            volumes = _walk_obj(volumes, _json)
            # We then need to merge them into a single dict and it will be ready
            # for docker-py.
            volumes = {k: v for volume in volumes for k, v in volume.items()}
            kwargs['volumes'] = volumes

        volumes.update(default_temp_volume._repr_json_())

        try:
            super().__call__(*args, **kwargs)
        finally:
            threading.Thread(
                target=self._cleanup_temp_volumes,
                args=(temp_volumes, default_temp_volume),
                daemon=False).start()

    def _cleanup_temp_volumes(self, temp_volumes, default_temp_volume):
        # Set the permission to allow cleanup of temp directories
        temp_volumes = [v.host_path for v in temp_volumes if os.path.exists(v.host_path)]
        if default_temp_volume._transformed:
            temp_volumes.append(default_temp_volume.host_path)

        remove_tmp_folder_apptainer(temp_volumes)


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
