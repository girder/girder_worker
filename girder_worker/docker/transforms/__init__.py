import sys
import uuid
import os
import tempfile
import six
import abc

from girder_worker_utils.transform import Transform


TEMP_VOLUME_MOUNT_PREFIX = '/mnt/girder_worker'


def _maybe_transform(obj, *args, **kwargs):
    if hasattr(obj, 'transform') and hasattr(obj.transform, '__call__'):
        return obj.transform(*args, **kwargs)

    return obj


class HostStdOut(Transform):
    def transform(self, **kwargs):
        from girder_worker.docker.io import (
            StdStreamWriter
        )
        return StdStreamWriter(sys.stdout)


class HostStdErr(Transform):
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
        self._host_path = host_path
        self._container_path = container_path
        self.mode = mode

    def _repr_json_(self):
        return {
            self.host_path: {
                'bind': self.container_path,
                'mode': self.mode
            }
        }

    def transform(self, **kwargs):
        return self.container_path

    @property
    def container_path(self):
        return self._container_path

    @property
    def host_path(self):
        return self._host_path


class _TemporaryVolumeMetaClass(abc.ABCMeta):
    @property
    def default(cls):
        return _DefaultTemporaryVolume()


class _TemporaryVolumeBase(Volume):
    def __init__(self, *arg, **kwargs):
        super(_TemporaryVolumeBase, self).__init__(*arg, **kwargs)
        self._transformed = False

    def _make_paths(self, host_dir=None):
        if host_dir is not None and not os.path.exists(host_dir):
            os.makedirs(host_dir)
        self._host_path = tempfile.mkdtemp(dir=host_dir)
        self._container_path = os.path.join(TEMP_VOLUME_MOUNT_PREFIX, uuid.uuid4().hex)


@six.add_metaclass(_TemporaryVolumeMetaClass)
class TemporaryVolume(_TemporaryVolumeBase):
    """
    This is a class used to represent a temporary directory on the host that will
    be mounted into a docker container. girder_worker will automatically attach a default
    temporary volume. This can be reference using `TemporaryVolume.default` class attribute.
    A temporary volume can also be create in a particular host directory by providing the
    `host_dir` param.
    :param host_dir
    """
    def __init__(self, host_dir=None):
        """
        :param host_dir: The root directory on the host to use when creating the
            the temporary host path.
        :type host_dir: str
        """
        super(TemporaryVolume, self).__init__(None, None)
        self.host_dir = host_dir
        self._instance = None
        self._transformed = False

    def transform(self, **kwargs):
        if not self._transformed:
            self._transformed = True
            self._make_paths(self.host_dir)

        return super(TemporaryVolume, self).transform(**kwargs)


class _DefaultTemporaryVolume(TemporaryVolume):
    """
    Place holder who delegates implementation to instance provide by transform(...) method
    An instance of the class is returned each time `TemporaryVolume.default` is accessed.
    When the docker_run task is executed the transform(...) method is call with an instance
    containing information about the actual default temporary volume associated with the
    task. The place holder then delgates all functionality to this instance.
    """
    def transform(self, _default_temp_volume=None, **kwargs):
        self._instance = _default_temp_volume
        self._transformed = True

        return self._instance.transform(**kwargs)

    @property
    def container_path(self):
        return self._instance.container_path

    @property
    def host_path(self):
        return self._instance.host_path


class NamedPipeBase(Transform):
    def __init__(self, name, container_path=None, host_path=None, volume=TemporaryVolume.default):
        super(NamedPipeBase, self).__init__()
        self._container_path = None
        self._host_path = None
        self._volume = None

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

    def cleanup(self, **kwargs):
        os.remove(self.host_path)


class NamedInputPipe(NamedPipeBase):
    """
    A named pipe that read from within a docker container.
    i.e. To stream data out of a container.
    """
    def __init__(self, name,  container_path=None, host_path=None, volume=TemporaryVolume.default):
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
    def __init__(self, name, container_path=None, host_path=None, volume=TemporaryVolume.default):
        super(NamedOutputPipe, self).__init__(name, container_path, host_path, volume)

    def transform(self, **kwargs):
        from girder_worker.docker.io import (
            NamedPipe,
            NamedPipeReader
        )
        super(NamedOutputPipe, self).transform(**kwargs)

        pipe = NamedPipe(self.host_path)
        return NamedPipeReader(pipe, self.container_path)


class VolumePath(Transform):
    def __init__(self, filename, volume=TemporaryVolume.default):
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


class ChunkedTransferEncodingStream(Transform):
    def __init__(self, url, headers={}, **kwargs):
        self.url = url
        self.headers = headers

    def transform(self, **kwargs):
        from girder_worker.docker.io import (
            ChunkedTransferEncodingStreamWriter
        )

        return ChunkedTransferEncodingStreamWriter(self.url, self.headers)
