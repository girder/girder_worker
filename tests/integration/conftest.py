import warnings
import pytest
import requests
import contextlib
import time
import functools
from girder_worker.utils import JobStatus
from datetime import timedelta, datetime

from requests_toolbelt.sessions import BaseUrlSession


class GirderSession(BaseUrlSession):
    def get_result(self, celery_id):
        r = self.post('integration_tests/result', data={
                'celery_id': celery_id})
        return r.text

# TODO: test with admin and non-admin user - are there (should there be)
# differences between girder-worker functionality between the two?
@pytest.fixture(scope='module',
                params=[['admin', 'letmein', 'http://127.0.0.1:8989/api/v1/']])
def session(request):
    username, password, api_url = request.param
    with GirderSession(base_url=api_url) as s:
        try:
            r = s.get('user/authentication',
                      auth=(username, password))
        except requests.ConnectionError:
            raise Exception(
                    'Unable to connect to %s.' % api_url)

        try:
            s.headers['Girder-Token'] = r.json()['authToken']['token']
        except KeyError:
            raise Exception(
                'Unable to login with user "%s", password "%s"' % (username, password))

        yield s


@pytest.fixture
def wait_for(session):

    @contextlib.contextmanager
    def _wait_for(job_id, predicate, timeout=20, interval=0.3, on_timeout=None):
        then = datetime.utcnow() + timedelta(seconds=timeout)
        timeout = True

        while datetime.utcnow() < then:
            r = session.get('job/' + job_id)

            if predicate(r.json()):
                timeout = False
                break

            time.sleep(interval)

        r = session.get('job/' + job_id)

        if timeout:
            if on_timeout is None:
                def on_timeout(j):
                    return 'Timed out waiting for %s' % 'job/%s' % j['_id']

            warnings.warn(on_timeout(r.json()))

        yield r.json()

    return _wait_for


@pytest.fixture
def wait_for_success(wait_for):

    def on_timeout(j):
        return 'Timed out waiting for %s to move into success state' % 'job/%s' % j['_id']

    return functools.partial(
        wait_for,
        predicate=lambda j: j['status'] == JobStatus.SUCCESS,
        on_timeout=on_timeout)


@pytest.fixture
def wait_for_error(wait_for):

    def on_timeout(j):
        return 'Timed out waiting for %s to move into error state' % 'job/%s' % (j['_id'])

    return functools.partial(
        wait_for,
        predicate=lambda j: j['status'] == JobStatus.ERROR,
        on_timeout=on_timeout)


# pytest hook for ordering test items after they have been
# collected. This uses 'priority' mark objects to order the
# tests, defaulting the priority of non-marked tests to 100.
def pytest_collection_modifyitems(items):
    def _get_priority(i):
        if i.get_marker('priority'):
            return i.get_marker('priority').args[0]
        return 100
    items.sort(key=_get_priority)
