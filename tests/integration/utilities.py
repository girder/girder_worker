import warnings
import functools
import contextlib
from girder_worker.utils import JobStatus
import time
from requests_toolbelt.sessions import BaseUrlSession
from datetime import timedelta, datetime


class GirderSession(BaseUrlSession):
    def __init__(self, *args, **kwargs):
        super(GirderSession, self).__init__(*args, **kwargs)

        self.wait_for_success = functools.partial(
            self.wait_for,
            predicate=lambda j:
                j['status'] == JobStatus.SUCCESS,
            on_timeout=lambda j:
                'Timed out waiting for job/%s to move into success state' % j['_id'])

        self.wait_for_error = functools.partial(
            self.wait_for,
            predicate=lambda j:
                j['status'] == JobStatus.ERROR,
            on_timeout=lambda j:
                'Timed out waiting for job/%s to move into error state' % j['_id'])

    def get_result(self, celery_id):
        r = self.post('integration_tests/result', data={
            'celery_id': celery_id})
        return r.text

    @contextlib.contextmanager
    def wait_for(self, job_id, predicate, timeout=20, interval=0.3, on_timeout=None):
        then = datetime.utcnow() + timedelta(seconds=timeout)
        timeout = True

        while datetime.utcnow() < then:
            r = self.get('job/' + job_id)

            if predicate(r.json()):
                timeout = False
                break

            time.sleep(interval)

        r = self.get('job/' + job_id)

        if timeout:
            if on_timeout is None:
                def on_timeout(j):
                    return 'Timed out waiting for %s' % 'job/%s' % j['_id']

            warnings.warn(on_timeout(r.json()))

        yield r.json()
