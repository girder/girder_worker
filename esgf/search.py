"""ESGF Search API."""

import six
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
