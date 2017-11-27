import os
import six
import json

from girder_worker.utils import JobStatus
import pytest


@pytest.mark.docker
def test_docker_run(session):
    r = session.post('integration_tests/docker/test_docker_run')
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]

        log = job['log']
        assert len(log) == 1
        assert log[0] == 'hello docker!\n'


@pytest.mark.docker
def test_docker_run_volume(session):
    fixture_dir = os.path.join('..', os.path.dirname(__file__), 'fixtures')
    params = {
        'fixtureDir': fixture_dir
    }
    r = session.post('integration_tests/docker/test_docker_run_mount_volume',
                     params=params)
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]

        log = job['log']
        assert len(log) == 2
        filepath = os.path.join(fixture_dir, 'read.txt')
        with open(filepath) as fp:
            assert log[0] == fp.read()


@pytest.mark.docker
def test_docker_run_named_pipe_output(session, tmpdir):
    params = {
        'tmpDir': tmpdir,
        'message': 'Dydh da'
    }
    r = session.post('integration_tests/docker/test_docker_run_named_pipe_output',
                     params=params)
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]

        log = job['log']
        assert len(log) == 1
        assert log[0] == params['message']


@pytest.mark.docker
def test_docker_run_girder_file_to_named_pipe(session, test_file, test_file_in_girder, tmpdir):

    params = {
        'tmpDir': tmpdir,
        'fileId': test_file_in_girder['_id']
    }
    r = session.post('integration_tests/docker/test_docker_run_girder_file_to_named_pipe',
                     params=params)
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]

        # Remove escaped chars
        log = [str(l) for l in job['log']]
        # join and remove trailing \n added by test script
        log = ''.join(log)[:-1]
        with open(test_file) as fp:
            assert log == fp.read()


@pytest.mark.docker
def test_docker_run_file_upload_to_item(session, girder_client, test_item):

    contents = 'Balaenoptera musculus'
    params = {
        'itemId': test_item['_id'],
        'contents': contents
    }
    r = session.post('integration_tests/docker/test_docker_run_file_upload_to_item',
                     params=params)
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]

    files = list(girder_client.listFile(test_item['_id']))

    assert len(files) == 1

    file_contents = six.BytesIO()
    girder_client.downloadFile(files[0]['_id'], file_contents)
    file_contents.seek(0)

    assert file_contents.read().strip() == contents


@pytest.mark.docker
def test_docker_run_girder_file_to_named_pipe_on_temp_vol(session, test_file, test_file_in_girder):
    """
    This is a simplified version of test_docker_run_girder_file_to_named_pipe
    it uses the TemporaryVolume, rather than having to setup the volumes
    'manually', this is the approach we should encourage.
    """

    params = {
        'fileId': test_file_in_girder['_id']
    }
    url = 'integration_tests/docker/test_docker_run_girder_file_to_named_pipe_on_temp_vol'
    r = session.post(url, params=params)
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]

        # Remove escaped chars
        log = [str(l) for l in job['log']]
        # join and remove trailing \n added by test script
        log = ''.join(log)[:-1]
        with open(test_file) as fp:
            assert log == fp.read()


@pytest.mark.docker
def test_docker_run_idiomatic_volume(session):
    fixture_dir = os.path.join('..', os.path.dirname(__file__), 'fixtures')
    params = {
        'fixtureDir': fixture_dir
    }
    r = session.post('integration_tests/docker/test_docker_run_mount_idiomatic_volume',
                     params=params)
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]

        log = job['log']
        assert len(log) == 2
        filepath = os.path.join(fixture_dir, 'read.txt')
        with open(filepath) as fp:
            assert log[0] == fp.read()


@pytest.mark.docker
def test_docker_run_progress_pipe(session):
    progressions = [
        {'message': 'Are there yet?', 'total': 100.0, 'current': 10.0},
        {'message': 'How about now?', 'total': 100.0, 'current': 20.0},
        {'message': 'Halfway there!', 'total': 100.0, 'current': 50.0},
        {'message': 'We have arrived!', 'total': 100.0, 'current': 100.0}
    ]
    r = session.post('integration_tests/docker/test_docker_run_progress_pipe', params={
        'progressions': json.dumps(progressions)
    })
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]

        progress = job['progress']

        del progress['notificationId']
        assert progress == progressions[-1]


@pytest.mark.docker
def test_docker_run_girder_file_to_volume(session, test_file, test_file_in_girder):
    params = {
        'fileId': test_file_in_girder['_id']
    }
    r = session.post('integration_tests/docker/test_docker_run_girder_file_to_volume',
                     params=params)
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]

        # Remove escaped chars
        log = [str(l) for l in job['log']]
        log = ''.join(log)
        with open(test_file) as fp:
            assert log == fp.read()


@pytest.mark.docker
def test_docker_run_transfer_encoding_stream(session, girder_client, test_file,
                                             test_file_in_girder, test_item):
    delimiter = '_please_dont_common_up_randomly_if_you_do_i_will_eat_my_hat!'
    params = {
        'itemId': test_item['_id'],
        'fileId': test_file_in_girder['_id'],
        'delimiter': delimiter
    }
    r = session.post('integration_tests/docker/test_docker_run_transfer_encoding_stream',
                     params=params)
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]

    files = list(girder_client.listFile(test_item['_id']))

    assert len(files) == 1

    file_contents = six.BytesIO()
    girder_client.downloadFile(files[0]['_id'], file_contents)
    file_contents.seek(0)
    chunks = file_contents.read().split(delimiter)
    chunks = [c for c in chunks if c != '']

    assert len(chunks) == 3

    with open(test_file) as fp:
        for chunk in chunks:
            assert chunk == fp.read(1024*64)


def test_docker_run_temporary_volume_root(session):
    params = {
        'prefix': 'prefix'
    }
    r = session.post('integration_tests/docker/test_docker_run_temporary_volume_root',
                     params=params)
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]
        assert len(job['log']) == 1
