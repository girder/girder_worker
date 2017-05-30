import pytest
import requests


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


# pytest hook for ordering test items after they have been
# collected. This uses 'priority' mark objects to order the
# tests, defaulting the priority of non-marked tests to 100.
def pytest_collection_modifyitems(items):
    def _get_priority(i):
        if i.get_marker('priority'):
            return i.get_marker('priority').args[0]
        return 100
    items.sort(key=_get_priority)
