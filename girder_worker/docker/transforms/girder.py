import errno
import os
import shutil
from girder_worker_utils.transform import Transform
from girder_worker_utils.transforms.girder_io import (
    GirderUploadJobArtifact,
    GirderClientTransform,
    GirderUploadToFolder,
    GirderUploadToItem
)
from . import TemporaryVolume, Connect, NamedOutputPipe, _maybe_transform


class ProgressPipe(Transform):

    def __init__(self, name='.girder_progress', volume=TemporaryVolume.default):
        self.name = name
        self._volume = volume

    def transform(self, task=None, **kwargs):
        from girder_worker.docker.stream_adapter import JobProgressAdapter

        self._volume.transform(**kwargs)

        # TODO What do we do is job_manager is None? When can it me None?
        job_mgr = task.job_manager
        # For now we are using JobProgressAdapter which is part of core, we should
        # probably add a copy to the docker package to break to reference to core.
        return Connect(NamedOutputPipe(self.name, volume=self._volume),
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


class GirderFileIdToVolume(GirderClientTransform):
    def __init__(self, _id, volume=TemporaryVolume.default, filename=None, **kwargs):
        super(GirderFileIdToVolume, self).__init__(**kwargs)
        self._file_id = str(_id)
        self._volume = volume
        self._filename = filename
        self._file_path = None

    def _create_file_path(self, root):
        if self._filename is None:
            # If no filename is explicitly passed, we read the filename from Girder
            # and put it in its own directory named by its UUID.
            filename = self.gc.getFile(self._file_id)['name']
            path = os.path.join(root, self._file_id)
            try:
                os.mkdir(path)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

            return os.path.join(self._file_id, filename), os.path.join(path, filename)
        else:
            return self._filename, os.path.join(root, self._filename)

    def transform(self, **kwargs):
        self._volume.transform(**kwargs)
        dir = self._volume.host_path
        rel_path, self._file_path = self._create_file_path(dir)

        self.gc.downloadFile(self._file_id, self._file_path)

        # Return the path inside the container
        return os.path.join(self._volume.container_path, rel_path)

    def cleanup(self, **kwargs):
        if self._file_path is not None:
            shutil.rmtree(self._file_path, ignore_errors=True)

    def _repr_model_(self):
        if self._filename:
            template = u'<{module}.{cls}: File ID={id} -> "{fname}">'
        else:
            template = u'<{module}.{cls}: File ID={id}>'
        return template.format(
            module=self.__module__, cls=self.__class__.__name__, id=self._file_id,
            fname=self._filename)


class GirderFolderIdToVolume(GirderClientTransform):
    def __init__(self, _id, volume=TemporaryVolume.default, folder_name=None, **kwargs):
        super(GirderFolderIdToVolume, self).__init__(**kwargs)
        self._folder_id = str(_id)
        self._volume = volume
        self._folder_name = folder_name
        self._folder_path = None

    def _create_folder_path(self, root):
        if self._folder_name is None:
            # If no folder name is explicitly passed, we read the filename from Girder
            # and put it in its own directory named by its UUID.
            self._folder_name = self.gc.getFolder(self._folder_id)['name']
        path = os.path.join(root, self._folder_id, self._folder_name)
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        return os.path.join(self._folder_id, self._folder_name), path

    def transform(self, **kwargs):
        self._volume.transform(**kwargs)
        dir = self._volume.host_path
        rel_path, self._folder_path = self._create_folder_path(dir)

        self.gc.downloadFolderRecursive(self._folder_id, self._folder_path)

        # Return the path inside the container
        return os.path.join(self._volume.container_path, rel_path)

    def cleanup(self, **kwargs):
        if self._folder_path is not None:
            shutil.rmtree(self._folder_path, ignore_errors=True)

    def _repr_model_(self):
        return '<%s.%s: Folder ID=%s -> "%s">' % (
            self.__module__, self.__class__.__name__, self._folder_id, self._folder_path)


class GirderUploadVolumePathToItem(GirderUploadToItem):
    def __init__(self, volumepath, item_id, delete_file=False, **kwargs):
        item_id = str(item_id)
        super(GirderUploadVolumePathToItem, self).__init__(item_id, delete_file, **kwargs)
        self._volumepath = volumepath

    # We ignore the "result"
    def transform(self, *args, **kwargs):
        path = _maybe_transform(self._volumepath, *args, **kwargs)

        return super(GirderUploadVolumePathToItem, self).transform(path)


class GirderUploadVolumePathToFolder(GirderUploadToFolder):
    def __init__(self, volumepath, folder_id, delete_file=False, **kwargs):
        super(GirderUploadVolumePathToFolder, self).__init__(str(folder_id), delete_file, **kwargs)
        self._volumepath = volumepath

    def transform(self, *args, **kwargs):
        path = _maybe_transform(self._volumepath, *args, **kwargs)
        return super(GirderUploadVolumePathToFolder, self).transform(path)


class GirderUploadVolumePathJobArtifact(GirderUploadJobArtifact):
    def __init__(self, volumepath, job_id=None, name=None, upload_on_exception=False, **kwargs):
        if job_id is not None:
            job_id = str(job_id)
        super(GirderUploadVolumePathJobArtifact, self).__init__(job_id, name, **kwargs)
        self._volumepath = volumepath
        self._upload_on_exception = upload_on_exception

    def transform(self, *args, **kwargs):
        path = _maybe_transform(self._volumepath, *args, **kwargs)
        return super(GirderUploadVolumePathJobArtifact, self).transform(path)

    def exception(self):
        if self._upload_on_exception:
            return self.transform()
