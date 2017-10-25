import sys


# TODO This will move to girder_work_utils repo.
class BaseTransform(object):
    __state__ = {}

    @classmethod
    def __obj__(cls, state):
        return cls(*state.get("args", []),
                   **state.get("kwargs", {}))

    def __json__(self):
        return {"_class": self.__class__.__name__,
                "__state__": self.__state__}

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj.__state__['args'] = args
        obj.__state__['kwargs'] = kwargs
        return obj

class StdOut(BaseTransform):
    def transform(self):
        from girder_worker.plugins.docker.io import StdStreamReader
        return StdStreamReader(sys.stdout)


class StdErr(BaseTransform):
    def transform(self):
        from girder_worker.plugins.docker.io import StdStreamReader
        return StdStreamReader(sys.stderr)


class ContainerStdOut(BaseTransform):

    def transform(self):
        return self

    def open(self):
        # noop
        pass


class ContainerStdErr(BaseTransform):

    def transform(self):
        return self

    def open(self):
        # noop
        pass


class ProgressPipe(BaseTransform):

    def __init__(self, path):
        super(ProgressPipe, self).__init__()
        self._path = path

    def transform(self, task):
        from girder_worker import utils
        from girder_worker.plugins.docker.io import (
            NamedPipe,
            NamedPipeReader,
            ReadStreamConnector
        )
        super(ProgressPipe, self).transform()
        job_mgr = task.job_manager
        pipe = NamedPipe(self.path)
        return ReadStreamConnector(NamedPipeReader(pipe), utils.JobProgressAdapter(job_mgr))


class NamedPipeBase(BaseTransform):
    def __init__(self, inside_path, outside_path):
        super(NamedPipeBase, self).__init__()

        self.inside_path = inside_path
        self.outside_path = outside_path


class NamedInputPipe(NamedPipeBase):
    """
    A named pipe that read from within a docker container.
    i.e. To stream data out of a container.
    """
    def __init__(self, inside_path, outside_path):
        super(NamedInputPipe, self).__init__(inside_path, outside_path)

    def transform(self):
        from girder_worker.plugins.docker.io import (
            NamedPipe,
            NamedPipeWriter
        )
        pipe = NamedPipe(self.outside_path)
        return NamedPipeWriter(pipe, self.inside_path)

class NamedOutputPipe(NamedPipeBase):
    """
    A named pipe that written to from within a docker container.
    i.e. To stream data out of a container.
    """
    def __init__(self, inside_path, outside_path):
        super(NamedInputPipe, self).__init__(inside_path, outside_path)

    def transform(self):
        from girder_worker.plugins.docker.io import (
            NamedPipe,
            NamedPipeReader
        )
        pipe = NamedPipe(self.outside_path)
        return NamedPipeReader(pipe, self.inside_path)

class Connect(BaseTransform):
    def __init__(self, input, output):
        super(Connect, self).__init__()
        self._input = input
        self._output = output

    def transform(self):
        from girder_worker.plugins.docker.io import (
            WriteStreamConnector,
            ReadStreamConnector,
        )
        if isinstance(self._output, NamedInputPipe):
            return WriteStreamConnector(self._input.transform(), self._output.transform())
        else:
            return ReadStreamConnector(self._input.transform(), self._output.transform())






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

