"""ESGF Search API."""

import re
import sys

import six
from six.moves import xrange
import requests


def raw(host, query):
    """Search the given esgf host with the given query object.

    :param str host: The host name (ex: ``"http://esg.ccs.ornl.gov/esg-search"``)
    :param dict query: The query parameters passed to the ESGF server
    :returns: The response from the ESGF server
    :rtype: dict
    :raises Exception: if the request fails

    See the ESGF REST API documented here:

    `https://github.com/ESGF/esgf.github.io/wiki/ESGF_Search_REST_API`_

    Example:
    >>> raw('http://esg.ccs.ornl.gov/esg-search', {'project': 'ACME'})
    ... # doctest: +ELLIPSIS
    {...}
    >>> raw('http://esg.ccs.ornl.gov/esg-search', {'badparam': ''})
    ... # doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    Exception: ESGF request failed with code ...
    """
    # Handle host name normalization
    if not re.match('[a-z]+://', host):
        host = 'http://' + host

    # Always return as a json object because nobody likes xml
    query['format'] = 'application/solr+json'

    req = requests.get(host.rstrip('/') + '/search', params=query)

    if not req.ok:
        raise Exception("ESGF request failed with code {0}".format(req.status_code))

    return req.json()


def facet(host, *fields):
    """Search facets on the given ESGF server.

    :param str host: The host name
    :param str fields: The fields to search for, if none are given, return all fields
    :return: A dictionary of fields -> ( values -> count )
    :rtype: dict

    Example:
    >>> import json
    >>> json.dumps(facet('http://esg.ccs.ornl.gov/esg-search', 'project'))
    ... # doctest: +ELLIPSIS
    '{"project": {...}}'
    """
    facets = '*'
    if len(fields):
        facets = ','.join(fields)

    query = {
        'limit': 0,  # don't return any file results
        'facets': facets
    }
    resp = raw(host, query)

    fields = resp['facet_counts']['facet_fields']

    def pairs(l):
        """Return pairs of the given list to construct a dict."""
        i = 0
        while i < len(l):
            yield l[i], l[i + 1]
            i += 2

    for key, val in six.iteritems(fields):
        fields[key] = dict(pairs(val))

    return fields


def _normalize_variable(doc, ivar):
    """Return a normalized representation of a variable.

    The normalized form of a variable has the following keys:

        * name: the variable name
        * cf: the CF standard name
        * desc: a description of the variable
        * units: the units of the variable

    If any of these fields are missing from the input, the corresponding value will
    be set to ``None``.

    :param dict doc: The file description
    :param integer ivar: The variable number inside the file
    :returns: A normalized variable description object
    """
    # Get the variable name inside the file
    v = {
        'name': doc['variable'][ivar],
        'cf': None,
        'desc': None,
        'units': None
    }

    # Get the standard CF name
    cf = doc.get('cf_standard_name', [])
    if ivar < len(cf):
        v['cf'] = cf[ivar]

    # Get the long name
    desc = doc.get('variable_long_name', [])
    if ivar < len(desc):
        v['desc'] = desc[ivar]

    # Get the units
    unit = doc.get('variable_units', [])
    if ivar < len(unit):
        v['desc'] = unit[ivar]

    return v


def _normalize_doc(doc):
    """Normalize a single document from a raw ESGF search."""
    norm = {
        'variables': [_normalize_variable(doc, i) for i in xrange(len(doc.get('variable', [])))]
    }
    for url in doc.get('url', []):
        url_parsed = url.split('|')
        unhandled = False
        if len(url_parsed) == 3:

            url_type = url_parsed[2].lower()
            if url_type == 'httpserver':
                norm['http'] = url_parsed[0]
            elif url_type == 'opendap':
                norm['dap'] = url_parsed[0]
            elif url_type == 'gridftp':
                norm['gridftp'] = url_parsed[0]
            else:
                unhandled = True
        else:
            unhandled = True

        if unhandled:
                six.print_('Unknown URL type "{0}"'.format(url), sys.stderr)

    norm['urls'] = doc.get('url', [])
    norm['size'] = doc.get('size')
    norm['timestamp'] = doc.get('timestamp')
    norm['project'] = doc.get('project', [None])[0]
    norm['id'] = doc.get('dataset_id')
    norm['experiment'] = doc.get('experiment', [None])[0]
    norm['node'] = doc.get('data_node')
    norm['metadata_format'] = doc.get('metadata_format')
    norm['regridding'] = doc.get('regridding')
    norm['title'] = doc.get('title')
    norm['type'] = doc.get('type')
    return norm


def _parse_results(result):
    """Normalize a search result from an ESGF server as a list of files with metadata.

    :param dict result: The raw search results
    :returns: A list of results in normalized form
    :rtype list:
    """
    docs = result.get('response', {}).get('docs', [])
    return [_normalize_doc(doc) for doc in docs]


def files(host, query):
    """Search an ESGF host for files returning a normalized result."""
    query['type'] = 'File'
    return _parse_results(raw(host, query))


def _sizeof_fmt(num, suffix='B'):
    """Return a pretty printed string for the given number."""
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


if __name__ == '__main__':

    import json
    import argparse

    from tabulate import tabulate

    parser = argparse.ArgumentParser(
        description='A commandline interface for ESGF queries.  One or more of the '
        'queries can be specified.  The resulting query will be the logical AND '
        'of the queries provided.'
    )

    parser.add_argument(
        'host',
        help='The ESGF host URL to search. For example, "esg.ccs.ornl.gov/esg-search"'
    )

    parser.add_argument(
        '-t', '--text',
        nargs=1,
        help='A free text search query in any metadata field'
    )

    parser.add_argument(
        '-p', '--project',
        nargs=1,
        help='Search by project'
    )

    parser.add_argument(
        '-l', '--limit',
        nargs=1,
        type=int,
        help='The maximum number of files to return'
    )

    parser.add_argument(
        '-o', '--offset',
        nargs=1,
        type=int,
        help='Start at this result'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Return the result as a json string'
    )

    parser.add_argument(
        '--url',
        choices=('http', 'dods', 'gridftp'),
        default='http',
        help='The url type to print'
    )

    args = parser.parse_args()

    # create a dict from the arguments
    q = {}
    if args.text is not None:
        q['query'] = args.text

    if args.project is not None:
        q['project'] = args.project

    if args.limit is not None:
        q['limit'] = args.limit

    if args.offset is not None:
        q['offset'] = args.offset

    # Limit the metadata returned from the server for CLI usage
    q['fields'] = 'size,timestamp,project,id,experiment,title,url'

    results = files(args.host, q)

    if args.json:
        print(json.dumps(results))
        sys.exit(0)

    def make_row(row):
        """Return a tuple of entries for the given result."""
        return (
            row['title'],
            row['timestamp'],
            row['project'],
            row['experiment'],
            _sizeof_fmt(row['size']),
            row[args.url]
        )

    headers = (
        'title',
        'timestamp',
        'project',
        'experiment',
        'size',
        'URL'
    )

    # construct a table of text to pretty print
    table = [make_row(row) for row in results]

    print(tabulate(table, headers=headers))
