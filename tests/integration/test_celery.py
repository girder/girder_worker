from girder_worker.utils import JobStatus
import pytest


@pytest.mark.sanitycheck
def test_session(session):
    r = session.get('user/me')
    assert r.status_code == 200
    assert r.json()['login'] == 'admin'
    assert r.json()['admin'] is True
    assert r.json()['status'] == 'enabled'


@pytest.mark.parametrize('endpoint', [
    'integration_tests/celery/test_task_delay',
    'integration_tests/celery/test_task_apply_async',
    'integration_tests/celery/test_task_signature_delay',
    'integration_tests/celery/test_task_signature_apply_async'],
    ids=['delay',
         'apply_async',
         'signature_delay',
         'signature_apply_async'])
def test_celery_task_success(session, endpoint):
    r = session.post(endpoint)
    assert r.status_code == 200

    with session.wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]

        assert 'celeryTaskId' in job
        assert session.get_result(job['celeryTaskId']) == '6765'


@pytest.mark.parametrize('endpoint', [
    'integration_tests/celery/test_task_delay_fails',
    'integration_tests/celery/test_task_apply_async_fails',
    'integration_tests/celery/test_task_signature_delay_fails',
    'integration_tests/celery/test_task_signature_apply_async_fails'],
    ids=['delay',
         'apply_async',
         'signature_delay',
         'signature_apply_async'])
def test_celery_task_fails(session, endpoint):
    r = session.post(endpoint)
    assert r.status_code == 200

    with session.wait_for_error(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.ERROR]

        assert job['log'][0].startswith('Exception: Intentionally failed after 0.5 seconds')


def test_celery_delay_custom_job_options(session):
    r = session.post('integration_tests/celery/test_task_delay_with_custom_job_options')
    assert r.status_code == 200

    with session.wait_for_success(r.json()['_id']) as job:
        assert job['title'] == 'TEST DELAY TITLE'


def test_celery_apply_async_custom_job_options(session):
    r = session.post('integration_tests/celery/test_task_apply_async_with_custom_job_options')
    assert r.status_code == 200

    with session.wait_for_success(r.json()['_id']) as job:
        assert job['title'] == 'TEST APPLY_ASYNC TITLE'


def test_celery_girder_client_generation(session):
    r = session.post('integration_tests/celery/test_girder_client_generation')
    assert r.status_code == 200

    with session.wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.SUCCESS]


def test_celery_girder_client_bad_token_fails(session):
    r = session.post('integration_tests/celery/test_girder_client_bad_token_fails')
    assert r.status_code == 200

    with session.wait_for_error(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.ERROR]


def test_celery_task_revoke(session):
    url = 'integration_tests/celery/test_task_revoke'
    r = session.post(url)
    assert r.status_code == 200

    with session.wait_for_canceled(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.CANCELED]


def test_celery_task_revoke_in_queue(session):
    url = 'integration_tests/celery/test_task_revoke_in_queue'
    r = session.post(url)
    assert r.status_code == 200

    with session.wait_for_canceled(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.CANCELED]
