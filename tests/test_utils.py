import sys
from girder_worker.utils import TeeStdOutCustomWrite, TeeStdErrCustomWrite, JobManager


def test_TeeStdOutCustomeWrite(capfd):
    _nonlocal = {'data': ''}

    def _append_to_data(message, **kwargs):
        _nonlocal['data'] += message

    with TeeStdOutCustomWrite(_append_to_data):
        sys.stdout.write('Test String')
        sys.stdout.flush()

    assert _nonlocal['data'] == 'Test String'
