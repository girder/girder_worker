import warnings
import pytest
import requests
import contextlib
import time
import functools
from girder_worker.utils import JobStatus
from datetime import timedelta, datetime


@pytest.fixture(scope='module')
def api_url():
    def _api_url(uri=''):
        return 'http://127.0.0.1:8989/api/v1/{}'.format(uri)
    return _api_url


# TODO: test with admin and non-admin user - are there (should there be)
# differences between girder-worker functionality between the two?
@pytest.fixture(scope='module')
def session(api_url, request):
    login = ('admin', 'letmein')
    with requests.Session() as s:
        try:
            r = requests.get(api_url('user/authentication'),
                             auth=login)
        except requests.ConnectionError:
            raise Exception(
                'Unable to connect to {}.'.format(api_url()))

        try:
            s.headers['Girder-Token'] = r.json()['authToken']['token']
        except KeyError:
            raise Exception(
                'Unable to login with user "{}", password "{}"'.format(*login))

        yield s


@pytest.fixture
def wait_for(session, api_url):

    @contextlib.contextmanager
    def _wait_for(job_id, predicate, timeout=20, interval=0.3, on_timeout=None):
        then = datetime.utcnow() + timedelta(seconds=timeout)
        timeout = True

        while datetime.utcnow() < then:
            r = session.get(api_url('job/{}'.format(job_id)))

            if predicate(r.json()):
                timeout = False
                break

            time.sleep(interval)

        r = session.get(api_url('job/{}'.format(job_id)))

        if timeout:
            if on_timeout is None:
                def on_timeout(j):
                    return 'Timed out waiting for {}'.format(
                        api_url('job/{}'.format(j['_id'])))

            warnings.warn(on_timeout(r.json()))

        yield r.json()

    return _wait_for


@pytest.fixture
def wait_for_success(wait_for, api_url):

    def on_timeout(j):
        return 'Timed out waiting for {} to move into success state'.format(
            api_url('job/{}'.format(j['_id'])))

    return functools.partial(
        wait_for,
        predicate=lambda j: j['status'] == JobStatus.SUCCESS,
        on_timeout=on_timeout)


@pytest.fixture
def wait_for_error(wait_for, api_url):

    def on_timeout(j):
        return 'Timed out waiting for {} to move into error state'.format(
            api_url('job/{}'.format(j['_id'])))

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
