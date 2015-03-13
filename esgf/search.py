"""ESGF Search API."""

import requests


def esgf_search(host, query):
    """Search the given esgf host with the given query.

    :param str host: The host name (ex: ``"http://esg.ccs.ornl.gov/esg-search"``)
    :param dict query: The query parameters passed to the ESGF server
    :returns: The response from the ESGF server
    :rtype: dict
    :raises Exception: if the request fails

    See the ESGF REST API documented here:

    `https://github.com/ESGF/esgf.github.io/wiki/ESGF_Search_REST_API`_

    Example:
    >>> esgf_search('http://esg.ccs.ornl.gov/esg-search', {'project': 'ACME'})
    ... # doctest: +ELLIPSIS
    {...}
    >>> esgf_search('http://esg.ccs.ornl.gov/esg-search', {'query': 'climate'})
    ... # doctest: +ELLIPSIS
    {...}
    """

    # Always return as a json object because nobody likes xml
    query['format'] = 'application/solr+json'

    req = requests.get(host.rstrip('/') + '/search', params=query)

    if not req.ok:
        raise Exception("ESGF request failed with code {0}".format(req.status_code))

    return req.json()
