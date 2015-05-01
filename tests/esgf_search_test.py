"""ESGF test methods."""

from httmock import HTTMock, urlmatch
import six
from six.moves.urllib import parse

from base import TestCase
from gaia import esgf
from gaia.esgf.search import _sizeof_fmt

last_host = None
last_query = {}


@urlmatch(netloc=r'(.*\.)?esgf-server[a-z]?.com')
def esgf_mock(url, request):
    """Mock an esgf request."""
    global last_host, last_query
    last_host = url.netloc
    last_query = parse.parse_qs(url.query)

    limit = int(last_query.get('limit', [10])[0])
    content = None

    if limit == 1:
        content = open(TestCase.data_path('esgf_search_limit1.json')).read()
    elif limit == 0:
        content = '{}'
    elif last_query.get('fields') is not None:
        if last_query['fields'][0] == 'variable':
            content = open(
                TestCase.data_path('esgf_search_variables.json')
            ).read()
        else:
            content = open(
                TestCase.data_path('esgf_search_fields.json')
            ).read()

    if six.PY3 and content is not None:
        content = bytes(content, 'utf-8')

    if content is not None:
        return {
            'content': content,
            'status_code': 200
        }
    else:
        return {
            'status_code': 400
        }


class SearchESGF(TestCase):

    """Test the ESGF search component with a mock server."""

    def test_limit1(self):
        """Test limit query."""
        with HTTMock(esgf_mock):
            r = esgf.search.files('esgf-server.com', {'limit': 1})
            self.assertEqual(len(r), 1)

    def test_limit0(self):
        """Test limit general query."""
        with HTTMock(esgf_mock):
            r = esgf.search.raw('esgf-server.com', {'limit': 0})
            self.assertEqual(len(r), 0)
            self.assertEqual(last_host, 'esgf-server.com')

    def test_fields(self):
        """Test restricting fields."""
        with HTTMock(esgf_mock):
            r = esgf.search.files(
                'esgf-server.com',
                {'fields': 'id,timestamp'}
            )

            for result in r:
                self.assertTrue('id' in result)
                self.assertTrue('timestamp' in result)

    def test_vars(self):
        """Test parsing of variables."""
        with HTTMock(esgf_mock):
            r = esgf.search.files('esgf-server.com', {'fields': 'variable'})

            for result in r:
                for v, i in six.iteritems(result['variables']):
                    self.assertEqual(v, i['name'])
                    self.assertTrue('units' in i)
                    self.assertTrue('desc' in i)
                    self.assertTrue('cf' in i)

    def test_sizeof(self):
        """Test sizeof formatting for CLI."""
        self.assertEqual(_sizeof_fmt(1), '1.0B')
        self.assertEqual(_sizeof_fmt(1024), '1.0KB')
        self.assertEqual(_sizeof_fmt(1024 * 1024), '1.0MB')
        self.assertEqual(_sizeof_fmt(2**80), '1.0YB')


if __name__ == '__main__':

    import unittest
    unittest.main()
