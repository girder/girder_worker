import json
import mock
import pytest

from girder_worker_utils.transform import Transform

from girder_worker.docker.io import (
    ChunkedTransferEncodingStreamWriter,
    FDReadStreamConnector,
    FDWriteStreamConnector,
    NamedPipeReader,
    NamedPipeWriter,
    StdStreamWriter
)

from girder_worker.docker.transforms import (
    ChunkedTransferEncodingStream,
    Connect,
    ContainerStdErr,
    ContainerStdOut,
    HostStdErr,
    HostStdOut,
    NamedInputPipe,
    NamedOutputPipe,
    NamedPipeBase,
    TEMP_VOLUME_MOUNT_PREFIX,
    TemporaryVolume,
    Volume,
    VolumePath,
    _maybe_transform
)


def test_maybe_transform_transforms():
    class T(Transform):
        def transform(self, **kargs):
            return 'FOOBAR'

    assert _maybe_transform(T()) == 'FOOBAR'


@pytest.mark.parametrize('obj', [
    'string',
    b'bytes',
    1,
    1.0,
    {'key': 'value'},
    ['some', 'list'],
    ('tuple', ),
    mock.Mock,
    object()])
def test_maybe_transform_passes_through(obj):
    assert _maybe_transform(obj) == obj


def test_HostStdOut_returns_StdStreamWriter():
    assert isinstance(HostStdOut().transform(), StdStreamWriter)


def test_HostStdErr_returns_StdStreamWriter():
    assert isinstance(HostStdErr().transform(), StdStreamWriter)


def test_ContainerStdOut_transform_retuns_self():
    cso = ContainerStdOut()
    assert cso.transform() == cso


def test_ContainerStdErr_transform_retuns_self():
    cse = ContainerStdErr()
    assert cse.transform() == cse


def test_Volume_container_path_is_container_path():
    v = Volume('/bogus/host_path', '/bogus/container_path')
    assert v.container_path == '/bogus/container_path'


def test_Volume_host_path_is_host_path():
    v = Volume('/bogus/host_path', '/bogus/container_path')
    assert v.host_path == '/bogus/host_path'


def test_Volume_transform_is_container_path():
    v = Volume('/bogus/host_path/', '/bogus/container_path')
    assert v.transform() == '/bogus/container_path'


def test_Volume_repr_json_is_json_serializable():
    v = Volume('/bogus/host_path/', '/bogus/container_path')
    json.dumps(v._repr_json_())


def test_TemporaryVolume_transform_creates_container_path():
    with mock.patch('girder_worker.docker.transforms.uuid.uuid4',
                    return_value=mock.Mock(hex='SOME_UUID')):
        tv = TemporaryVolume()

        assert tv.container_path is None
        assert tv.transform() == '{}/SOME_UUID'.format(TEMP_VOLUME_MOUNT_PREFIX)
        assert tv.container_path == '{}/SOME_UUID'.format(TEMP_VOLUME_MOUNT_PREFIX)


def test_TemporaryVolume_host_path_is_temporary_directory():
    with mock.patch('girder_worker.docker.transforms.tempfile.mkdtemp', return_value='/bogus/path'):
        tv = TemporaryVolume()

        assert tv.host_path is None
        tv.transform()
        assert tv.host_path == '/bogus/path'


def test_TemporaryVolume_host_dir_prepended_to_host_path():
    with mock.patch('girder_worker.docker.transforms.tempfile.mkdtemp') as mock_mkdtemp:
        with mock.patch('girder_worker.docker.transforms.os.path.exists', return_value=True):
            TemporaryVolume(host_dir='/some/preexisting/directory').transform()
            mock_mkdtemp.assert_called_once_with(dir='/some/preexisting/directory')


# TODO:  _DefaultTemporaryVolume and Metaclass behavior


def test_NamedPipeBase_container_path_returns_container_path_plus_name():
    npb = NamedPipeBase('test',
                        container_path='/bogus/container_path',
                        host_path='/bogus/host_path')

    assert npb.container_path == '/bogus/container_path/test'


def test_NamedPipeBase_host_path_returns_host_path_plus_name():
    npb = NamedPipeBase('test',
                        container_path='/bogus/container_path',
                        host_path='/bogus/host_path')

    assert npb.host_path == '/bogus/host_path/test'


def test_NamedPipeBase_pass_volume_return_volume_container_path_plus_name():
    v = Volume('/bogus/volume/host_path', '/bogus/volume/container_path')
    npb = NamedPipeBase('test', volume=v)

    assert npb.container_path == '/bogus/volume/container_path/test'


def test_NamedPipeBase_pass_volume_return_volume_host_path_plus_name():
    v = Volume('/bogus/volume/host_path', '/bogus/volume/container_path')
    npb = NamedPipeBase('test', volume=v)

    assert npb.host_path == '/bogus/volume/host_path/test'


def test_NamedInputPipe_transform_returns_NamedPipeWriterr():
    nip = NamedInputPipe('test',
                         container_path='/bogus/container_path',
                         host_path='/bogus/host_path')
    with mock.patch('girder_worker.docker.io.os.mkfifo'):
        assert isinstance(nip.transform(), NamedPipeWriter)


def test_NamedOutputPipe_transform_returns_NamedPipeReader():
    nop = NamedOutputPipe('test',
                          container_path='/bogus/container_path',
                          host_path='/bogus/host_path')
    with mock.patch('girder_worker.docker.io.os.mkfifo'):
        assert isinstance(nop.transform(), NamedPipeReader)


def test_VolumePath_transform_returns_container_path_with_no_args():
    v = Volume('/bogus/volume/host_path', '/bogus/volume/container_path')
    vp = VolumePath('test', v)

    assert vp.transform() == '/bogus/volume/container_path/test'


def test_VolumePath_transform_returns_host_path_with_args():
    v = Volume('/bogus/volume/host_path', '/bogus/volume/container_path')
    vp = VolumePath('test', v)

    assert vp.transform('TASK_DATA') == '/bogus/volume/host_path/test'


def test_Connect_transform_returns_FDWriteStreamConnector_if_output_is_NamedInputPipe(istream):
    nip_mock = mock.MagicMock(spec=NamedInputPipe(
        'test',
        container_path='/bogus/container_path',
        host_path='/bogus/host_path'))
    connection = Connect(istream, nip_mock)
    assert isinstance(connection.transform(), FDWriteStreamConnector)


def test_Connect_transform_returns_FDReadStreamConnector_if_input_is_NamedOutputPipe(ostream):
    nop_mock = mock.MagicMock(spec=NamedOutputPipe(
        'test',
        container_path='/bogus/container_path',
        host_path='/bogus/host_path'))
    connection = Connect(nop_mock, ostream)
    assert isinstance(connection.transform(), FDReadStreamConnector)


def test_Connect_transform_throws_exception_if_no_NamedPipe_provided(istream, ostream):
    with pytest.raises(TypeError):
        Connect(istream, ostream).transform()


def test_ChunkedTransferEncodingStream_transform_returns_ChunkedTransferEncodingStreamWriter():
    ctes = ChunkedTransferEncodingStream('http://bogusurl.com')
    with mock.patch('girder_worker.docker.io.httplib.HTTPConnection', autospec=True):
        assert isinstance(ctes.transform(), ChunkedTransferEncodingStreamWriter)


def test_ChunkedTransferEncodingStream_transform_calls_ChunkedTransferEncodingWriter_with_args():
    ctes = ChunkedTransferEncodingStream('http://bogusurl.com')
    with mock.patch('girder_worker.docker.io.ChunkedTransferEncodingStreamWriter',
                    spec=True) as ctesw_class_mock:
        ctes.transform()
        ctesw_class_mock.assert_called_once_with('http://bogusurl.com', {})


def test_ChunkedTransferEncodingStream_transform_calls_ChunkedTransferEncodingWriter_with_headers():
    ctes = ChunkedTransferEncodingStream(
        'http://bogusurl.com',
        {'Key1': 'Value1', 'Key2': 'Value2'})

    with mock.patch('girder_worker.docker.io.ChunkedTransferEncodingStreamWriter',
                    spec=True) as ctesw_class_mock:
        ctes.transform()
        ctesw_class_mock.assert_called_once_with(
            'http://bogusurl.com',
            {'Key1': 'Value1', 'Key2': 'Value2'})
