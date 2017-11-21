import sys
import six
import uuid
import os
import shutil
import tempfile

from girder_worker_utils.transform import Transform
from girder_worker_utils.transforms.girder_io import (
    GirderClientTransform,
    GirderUploadToItem,
    GirderFileId
)
from girder_worker.core.utils import JobProgressAdapter

TEMP_VOLUME_MOUNT_PREFIX = '/mnt/girder_worker'

def _maybe_transform(obj, *args, **kwargs):
    if hasattr(obj, 'transform') and hasattr(obj.transform, '__call__'):
        return obj.transform(*args, **kwargs)

    return obj

class StdOut(Transform):
    def transform(self, **kwargs):
        from girder_worker.docker.io import (
            StdStreamWriter
        )
        return StdStreamWriter(sys.stdout)


class StdErr(Transform):
    def transform(self, **kwargs):
        from girder_worker.docker.io import (
            StdStreamWriter
        )
        return StdStreamWriter(sys.stderr)


class ContainerStdOut(Transform):

    def transform(self, **kwargs):
        return self

    def open(self):
        # noop
        pass


class ContainerStdErr(Transform):

    def transform(self, **kwargs):
        return self

    def open(self):
        # noop
        pass

class Volume(Transform):
    def __init__(self, host_path, container_path, mode='rw'):
        self.host_path = host_path
        self.container_path = container_path
        self.mode = mode

    def transform(self, **kwargs):
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

    def transform(self, temp_volume=None, **kwargs):
        # We save the runtime instances provide by the task, we delegate to this
        # instance
        if temp_volume is not None:
            self._instance = temp_volume
        return self._instance.transform(**kwargs)

    def cleanup(self):
        self._instance.cleanup()

    @property
    def container_path(self):
        return self._instance.container_path

    @property
    def host_path(self):
        return self._instance.host_path

class ProgressPipe(Transform):

    def __init__(self, name='.girder_progress', volume=TemporaryVolume()):
        self.name = name
        self._volume = volume


    def transform(self, task=None, **kwargs):
        from girder_worker import utils
        from girder_worker.docker.io import (
            NamedPipe,
            NamedPipeReader,
            ReadStreamConnector
        )
        self._volume.transform(**kwargs)

        # TODO What do we do is job_manager is None? When can it me None?
        job_mgr = task.job_manager
        # For now we are using JobProgressAdapter which is part of core, we should
        # probably add a copy to the docker package to break to reference to core.
        return Connect(NamedOutputPipe(self.name, self._volume),
                       JobProgressAdapter(job_mgr)).transform(**kwargs)

class NamedPipeBase(Transform):
    def __init__(self, name, container_path=None, host_path=None, volume=TemporaryVolume()):
        super(NamedPipeBase, self).__init__()
        self._container_path = None
        self._host_path = None
        self._volume  = None

        if container_path is not None and host_path is not None:
            self._container_path = container_path
            self._host_path = host_path
        else:
            self._volume = volume

        self.name = name

    def transform(self, **kwargs):
        if self._volume is not None:
            self._volume.transform(**kwargs)

    @property
    def container_path(self):
        if self._container_path is not None:
            return os.path.join(self._container_path, self.name)
        else:
            return os.path.join(self._volume.container_path, self.name)

    @property
    def host_path(self):
        if self._host_path is not None:
            return os.path.join(self._host_path, self.name)
        else:
            return os.path.join(self._volume.host_path, self.name)

class NamedInputPipe(NamedPipeBase):
    """
    A named pipe that read from within a docker container.
    i.e. To stream data out of a container.
    """
    def __init__(self, name,  container_path=None, host_path=None, volume=TemporaryVolume()):
        super(NamedInputPipe, self).__init__(name, container_path, host_path, volume)

    def transform(self, **kwargs):
        from girder_worker.docker.io import (
            NamedPipe,
            NamedPipeWriter
        )
        super(NamedInputPipe, self).transform(**kwargs)

        pipe = NamedPipe(self.host_path)
        return NamedPipeWriter(pipe, self.container_path)

class NamedOutputPipe(NamedPipeBase):
    """
    A named pipe that written to from within a docker container.
    i.e. To stream data out of a container.
    """
    def __init__(self, name, container_path=None, host_path=None, volume=TemporaryVolume()):
        super(NamedOutputPipe, self).__init__(name, container_path, host_path, volume)

    def transform(self, **kwargs):
        from girder_worker.docker.io import (
            NamedPipe,
            NamedPipeReader
        )
        super(NamedOutputPipe, self).transform(**kwargs)

        pipe = NamedPipe(self.host_path)
        return NamedPipeReader(pipe, self.container_path)

class FilePath(Transform):
    def __init__(self, filename, volume=TemporaryVolume()):
        self.filename = filename
        self._volume = volume

    def transform(self, *pargs, **kwargs):
        self._volume.transform(**kwargs)
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

    def transform(self, **kwargs):
        from girder_worker.docker.io import (
            WriteStreamConnector,
            ReadStreamConnector,
        )
        input = _maybe_transform(self._input, **kwargs)
        output = _maybe_transform(self._output, **kwargs)
        if isinstance(self._output, NamedInputPipe):
            return WriteStreamConnector(input, output)
        else:
            return ReadStreamConnector(input, output)

    def _repr_model_(self):
        """
        The method is called before save the argument in the job model.
        """
        return str(self)

class GirderFileIdToStream(GirderClientTransform):
    def __init__(self, _id, **kwargs):
        super(GirderFileIdToStream, self).__init__(**kwargs)
        self.file_id = _id

    def transform(self, **kwargs):
        from girder_worker.docker.io import (
            GirderFileStreamReader
        )
        return GirderFileStreamReader(self.gc, self.file_id)

class GirderFileIdToVolume(GirderFileId):
    def __init__(self, _id, volume=TemporaryVolume(), **kwargs):
        super(GirderFileIdToVolume, self).__init__(_id,**kwargs)
        self._volume = volume

    def transform(self, **kwargs):
        self._volume.transform(**kwargs)
        self._dir = self._volume.host_path
        super(GirderFileIdToVolume, self).transform()

        # Return the path inside the container
        return os.path.join(self._volume.container_path,
                            os.path.basename(self.file_path))

    def cleanup(self, **kwargs):
        if hasattr(self, 'file_path'):
            os.remove(self.file_path)

class GirderUploadFilePathToItem(GirderUploadToItem):
    def __init__(self, filepath, item_id,  delete_file=False, **kwargs):
        super(GirderUploadFilePathToItem, self).__init__(item_id, delete_file, **kwargs)
        self._filepath = filepath

    # We ignore the "result"
    def transform(self, *args, **kwargs):
        path = _maybe_transform(self._filepath, *args, **kwargs)

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

