import os
from girder_worker_utils.transform import Transform
from girder_worker_utils.transforms.girder_io import (
    GirderClientTransform,
    GirderUploadToItem,
    GirderFileId
)


from . import (
    TemporaryVolume,
    Connect,
    NamedOutputPipe,
    _maybe_transform
)


class ProgressPipe(Transform):

    def __init__(self, name='.girder_progress', volume=TemporaryVolume.default):
        self.name = name
        self._volume = volume

    def transform(self, task=None, **kwargs):
        from girder_worker.core.utils import JobProgressAdapter

        self._volume.transform(**kwargs)

        # TODO What do we do is job_manager is None? When can it me None?
        job_mgr = task.job_manager
        # For now we are using JobProgressAdapter which is part of core, we should
        # probably add a copy to the docker package to break to reference to core.
        return Connect(NamedOutputPipe(self.name, self._volume),
                       JobProgressAdapter(job_mgr)).transform(**kwargs)


class GirderFileIdToStream(GirderClientTransform):
    def __init__(self, _id, **kwargs):
        super(GirderFileIdToStream, self).__init__(**kwargs)
        self.file_id = _id

    def transform(self, **kwargs):
        from girder_worker.docker.io.girder import (
            GirderFileStreamReader
        )
        return GirderFileStreamReader(self.gc, self.file_id)


class GirderFileIdToVolume(GirderFileId):
    def __init__(self, _id, volume=TemporaryVolume.default, **kwargs):
        super(GirderFileIdToVolume, self).__init__(_id, **kwargs)
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
