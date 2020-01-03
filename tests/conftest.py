import io
import mock
import pytest
import random

from girder_client import GirderClient


@pytest.fixture
def mock_gc():
    mgc = mock.MagicMock(spec=GirderClient)
    mgc.getFile.return_value = {'_id': 'BOGUS_ID', 'name': 'bogus.txt'}
    return mgc


@pytest.fixture
def patch_mkdir():
    with mock.patch('os.mkdir') as mkdir_mock:
        yield mkdir_mock


@pytest.fixture
def patch_makedirs():
    with mock.patch('os.makedirs') as m:
        yield m


@pytest.fixture
def stream():
    class MockFileStream(io.BytesIO):
        def __init__(self, fd, *args, **kwargs):
            self._fd = fd
            super(MockFileStream, self).__init__(*args, **kwargs)

        def fileno(self):
            return self._fd

        @property
        def data(self):
            return self.getvalue()

        @data.setter
        def data(self, data):
            self.truncate()
            self.write(data)
            self.seek(0)
    return MockFileStream(random.randrange(4, 100))


istream = stream
ostream = stream
