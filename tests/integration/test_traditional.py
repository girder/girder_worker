from girder_worker.utils import JobStatus
import pytest


def test_traditional_job_custom_task_name(session, api_url, wait_for_success, get_result):
    r = session.post(api_url('integration_tests/test_traditional_job_custom_task_name'))
    assert r.status_code == 200

    with wait_for_success(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.SUCCESS]

        assert 'celeryTaskId' in job
        assert get_result(job['celeryTaskId']) == '6765'
