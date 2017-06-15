import pytest
import requests
from .utilities import GirderSession


def pytest_addoption(parser):
    parser.addoption('--girder', action='store', default='http://127.0.0.1:8989/',
                     help='Specify a different server to run against')


@pytest.fixture(scope='module')
def api_url(request):
    return request.config.getoption('--girder') + 'api/v1/'


# TODO: test with admin and non-admin user - are there (should there be)
# differences between girder-worker functionality between the two?
@pytest.fixture(scope='module',
                params=[['admin', 'letmein']],
                ids=['admin'])
def session(request, api_url):
    username, password = request.param
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
