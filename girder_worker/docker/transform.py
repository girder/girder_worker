import sys

from girder_worker_utils.transform import Transform
from girder_worker_utils.transforms.girder_io import GirderClientTransform


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


class NamedPipeBase(Transform):
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
        from girder_worker.docker.io import (
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
        super(NamedOutputPipe, self).__init__(inside_path, outside_path)

    def transform(self):
        from girder_worker.docker.io import (
            NamedPipe,
            NamedPipeReader
        )
        pipe = NamedPipe(self.outside_path)
        return NamedPipeReader(pipe, self.inside_path)

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

