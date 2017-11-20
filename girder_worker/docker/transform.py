import sys
import six
import uuid
import os
import shutil
import tempfile

from girder_worker_utils.transform import Transform
from girder_worker_utils.transforms.girder_io import (
    GirderClientTransform,
    GirderUploadToItem
)

TEMP_VOLUME_MOUNT_PREFIX = '/mnt/girder_worker'

def _maybe_transform(obj, *args):
    if hasattr(obj, 'transform') and hasattr(obj.transform, '__call__'):
        return obj.transform()

    return obj

class StdOut(Transform):
    def transform(self):
        from girder_worker.docker.io import (
            StdStreamWriter
        )
        return StdStreamWriter(sys.stdout)


class StdErr(Transform):
    def transform(self):
        from girder_worker.docker.io import (
            StdStreamWriter
        )
        return StdStreamWriter(sys.stderr)


class ContainerStdOut(Transform):

    def transform(self):
        return self

    def open(self):
        # noop
        pass


class ContainerStdErr(Transform):

    def transform(self):
        return self

    def open(self):
        # noop
        pass


class ProgressPipe(Transform):

    def __init__(self, path):
        super(ProgressPipe, self).__init__()
        self._path = path

    def transform(self, task):
        from girder_worker import utils
        from girder_worker.docker.io import (
            NamedPipe,
            NamedPipeReader,
            ReadStreamConnector
        )
        super(ProgressPipe, self).transform()
        job_mgr = task.job_manager
        pipe = NamedPipe(self.path)
        return ReadStreamConnector(NamedPipeReader(pipe), utils.JobProgressAdapter(job_mgr))

class Volume(Transform):
    def __init__(self, host_path, container_path, mode='rw'):
        self.host_path = host_path
        self.container_path = container_path
        self.mode = mode

    def transform(self):
        return {
            self.host_path: {
                'bind': self.container_path,
                'mode': self.mode
            }
        }

class _TemporaryVolume(Volume):
    def __init__(self, dir=None):
        self._dir = dir
        super(_TemporaryVolume, self).__init__(tempfile.mkdtemp(dir=self._dir),
            os.path.join(TEMP_VOLUME_MOUNT_PREFIX, uuid.uuid4().hex))

    def cleanup(self):
        if os.path.exists(self.host_path):
            shutil.rmtree(self.host_path)

class _TemporaryVolumeSingleton(type):
    def __init__(cls, name, bases, dict):
        super(_TemporaryVolumeSingleton, cls).__init__(name, bases, dict)
        cls._instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(_TemporaryVolumeSingleton, cls).__call__(*args, **kwargs)
        return cls._instance


@six.add_metaclass(_TemporaryVolumeSingleton)
class TemporaryVolume:
    dir = None

    def __init__(self):
        self._instance = None

    @property
    def _task_instance(self):
        if self._instance is None:
            # This is not ideal however, if allows use to have a single share temp
            # volume across a task.

            from girder_worker.app import app
            self._instance = app.current_task._temp_volume

        return self._instance

    def transform(self):
        return self._task_instance.transform()

    def cleanup(self):
        self._task_instance.cleanup()

    @property
    def container_path(self):
        return self._task_instance.container_path

    @property
    def host_path(self):
        return self._task_instance.host_path


class NamedPipeBase(Transform):
    def __init__(self, name, container_path=None, host_path=None, volume=TemporaryVolume()):
        super(NamedPipeBase, self).__init__()

        if container_path is not None and host_path is not None:
            self._container_path = container_path
            self._host_path = host_path
        else:
            self._volume = volume

        self.name = name

    @property
    def container_path(self):
        return os.path.join(self._volume.container_path, self.name)

    @property
    def host_path(self):
        return os.path.join(self._volume.host_path, self.name)

class NamedInputPipe(NamedPipeBase):
    """
    A named pipe that read from within a docker container.
    i.e. To stream data out of a container.
    """
    def __init__(self, name, volume=None):
        super(NamedInputPipe, self).__init__(name, volume)

    def transform(self):
        from girder_worker.docker.io import (
            NamedPipe,
            NamedPipeWriter
        )

        pipe = NamedPipe(self.host_path)
        return NamedPipeWriter(pipe, self.container_path)

class NamedOutputPipe(NamedPipeBase):
    """
    A named pipe that written to from within a docker container.
    i.e. To stream data out of a container.
    """
    def __init__(self, inside_path, outside_path):
        super(NamedOutputPipe, self).__init__(inside_path, outside_path)

    def transform(self):
        from girder_worker.docker.io import (
            NamedPipe,
            NamedPipeReader
        )

        pipe = NamedPipe(self.host_path)
        return NamedPipeReader(pipe, self.container_path)

class FilePath(Transform):
    def __init__(self, filename, volume=TemporaryVolume()):
        self.filename = filename
        self._volume = volume

    def transform(self, *pargs):
        # If we are being called with arguments, then this is the execution of
        # girder_result_hooks, so return the host_path
        if len(pargs) > 0:
            return os.path.join(self._volume.host_path, self.filename)
        else:
            return os.path.join(self._volume.container_path, self.filename)

class Connect(Transform):
    def __init__(self, input, output):
        super(Connect, self).__init__()
        self._input = input
        self._output = output

    def transform(self):
        from girder_worker.docker.io import (
            WriteStreamConnector,
            ReadStreamConnector,
        )
        if isinstance(self._output, NamedInputPipe):
            return WriteStreamConnector(self._input.transform(), self._output.transform())
        else:
            return ReadStreamConnector(self._input.transform(), self._output.transform())

    def _repr_model_(self):
        """
        The method is called before save the argument in the job model.
        """
        return str(self)

class GirderFileToStream(GirderClientTransform):
    def __init__(self, _id, **kwargs):
        super(GirderFileToStream, self).__init__(**kwargs)
        self.file_id = _id

    def transform(self):
        from girder_worker.docker.io import (
            GirderFileStreamReader
        )
        return GirderFileStreamReader(self.gc, self.file_id)

class GirderUploadFilePathToItem(GirderUploadToItem):
    def __init__(self, filepath, item_id,  delete_file=False, **kwargs):
        super(GirderUploadFilePathToItem, self).__init__(item_id, delete_file, **kwargs)
        self._filepath = filepath

    # We ignore the "result"
    def transform(self, *args):
        path = _maybe_transform(self._filepath, *args)

        return super(GirderUploadFilePathToItem, self).transform(path)

# class GirderFileToUploadStream(GirderClientTransform):
#     def __init__(self, _id, **kwargs):
#         super(GirderFileToStream, self).__init__(**kwargs)
#         self.file_id = _id
#
#     def transform(self):
#         from girder_worker.docker.io import (
#             GirderFileStreamPushAdapter
#         )
#
#         return GirderFileStreamFetchAdapter(self.file_id, self.client)


#
# For example:
# docker_run.delay(image, stream_connectors=[Connect(NamedOutputPipe('my/pipe'), StdOut())]
# docker_run.delay(image, stream_connectors=[Connect(ContainerStdOut(), StdErr())]
# docker_run.delay(image, stream_connectors=[Connect(ContainerStdOut(), StdErr())]
# docker_run.delay(image, stream_connectors=[Connect(GirderFile(id), NamedInputPipe(my/girder/pipe))]
# docker_run.delay(image, stream_connectors=[ProgressPipe('write/your/progress/here')]
# docker_run.delay(image, stream_connectors=[Connect(ContainerStdOut(), GirderFileId(id))]
#                                           output                                                  input
# docker_run.delay(image, container_args=[Connect(NamedPipe('my/input/pipe'), StdOut()), Connect(GirderFileId(id), NamedPipe('my/girder/pipe'))])
#
# args passed to container: my/input/pipe, my/girder/pipe
#

