import warnings
import pytest
import requests
import contextlib
import time
import functools
from girder_worker.utils import JobStatus
from datetime import timedelta, datetime


def pytest_addoption(parser):
        parser.addoption('--girder', action='store', default='http://127.0.0.1:8989',
                         help='my option: type1 or type2')


@pytest.fixture(scope='module')
def girder_url(request):
        return request.config.getoption('--girder')


@pytest.fixture(scope='module')
def api_url():
    def _api_url(uri=u''):
        return u'http://127.0.0.1:8989/api/v1/' + uri
    return _api_url


@pytest.fixture
def get_result(session, api_url):
    def _get_result(celery_id):
        r = session.post(api_url('integration_tests/result'), data={'celery_id': celery_id})
        return r.text
    return _get_result


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
                'Unable to connect to %s.' % api_url())

        try:
            s.headers['Girder-Token'] = r.json()['authToken']['token']
        except KeyError:
            raise Exception(
                'Unable to login with user "%s", password "%s"' % login)

        yield s


@pytest.fixture
def wait_for(session, api_url):

    @contextlib.contextmanager
    def _wait_for(job_id, predicate, timeout=20, interval=0.3, on_timeout=None):
        then = datetime.utcnow() + timedelta(seconds=timeout)
        timeout = True

        while datetime.utcnow() < then:
            r = session.get(api_url('job/' + job_id))

            if predicate(r.json()):
                timeout = False
                break

            time.sleep(interval)

        r = session.get(api_url('job/' + job_id))

        if timeout:
            if on_timeout is None:
                def on_timeout(j):
                    return 'Timed out waiting for %s' % api_url('job/%s' % j['_id'])

            warnings.warn(on_timeout(r.json()))

        yield r.json()

    return _wait_for


@pytest.fixture
def wait_for_success(wait_for, api_url):

    def on_timeout(j):
        return 'Timed out waiting for %s to move into success state' % api_url('job/%s' % j['_id'])

    return functools.partial(
        wait_for,
        predicate=lambda j: j['status'] == JobStatus.SUCCESS,
        on_timeout=on_timeout)


@pytest.fixture
def wait_for_error(wait_for, api_url):

    def on_timeout(j):
        return 'Timed out waiting for %s to move into error state' % api_url('job/%s' % (j['_id']))

    return functools.partial(
        wait_for,
        predicate=lambda j: j['status'] == JobStatus.ERROR,
        on_timeout=on_timeout)


# pytest hooks for ordering test items after they have been collected
# and ensuring tests marked with sanitycheck run first.
# pytest_runtest_makereport and pytest_runtest_setup are used to xfail
# all tests if any of the sanitychecks fail.
def pytest_collection_modifyitems(items):
    items.sort(key=lambda i: -1 if i.get_marker('sanitycheck') else 1)


def pytest_runtest_makereport(item, call):
    if 'sanitycheck' in item.keywords:
        if call.excinfo is not None:
            session = item.parent.parent
            session._sanitycheckfailed = item


def pytest_runtest_setup(item):
        session = item.parent.parent
        sanitycheckfailed = getattr(session, '_sanitycheckfailed', None)
        if sanitycheckfailed is not None:
            pytest.xfail('previous test failed (%s)' % sanitycheckfailed.name)
