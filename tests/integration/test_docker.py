import os

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
        'tmpDir': tmpdir
    }
    r = session.post('integration_tests/docker/test_docker_run_named_pipe_output',
                     params=params)
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]

        log = job['log']
        assert len(log) == 1
        assert log[0] == '/mnt/girder_worker/data/output_pipe'
