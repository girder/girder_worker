from girder_worker.utils import JobStatus
import pytest


@pytest.mark.priority(10)
def test_session(session, api_url):
    r = session.get(api_url('user/me'))
    assert r.status_code == 200
    assert r.json()['login'] == 'admin'
    assert r.json()['admin'] is True
    assert r.json()['status'] == 'enabled'


def test_celery_task_delay(session, api_url, wait_for_success):
    r = session.post(api_url('integration_tests/test_celery_task_delay'))
    assert r.status_code == 200

    with wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]
