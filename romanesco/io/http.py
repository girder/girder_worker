import os
import re
import requests


def _readFilenameFromResponse(request):
    """
    This helper will derive a filename from the HTTP response, first attempting
    to use the content disposition header, otherwise falling back to the last
    token of the URL.
    """
    match = re.search('filename="(.*)"', request.headers['Content-Disposition'])

    if match is None:
        return [t for t in request.url.split('/') if t][-1]
    else:
        return match.group(1)


def fetch(spec, **kwargs):
    """
    Downloads an input file via HTTP using requests.
    """
    tmpDir = kwargs['_tmpDir']  # TODO create if not set?

    if 'url' not in spec:
        raise Exception('No URL specified for HTTP input.')

    method = getattr(requests, spec.get('method', 'get').lower())
    request = method(spec['url'], headers=spec.get('headers', {}))

    try:
        request.raise_for_status()
    except:
        print 'HTTP fetch failed (%s). Response: %s' % \
            (spec['url'], request.text)
        raise

    filename = spec.get('filename', _readFilenameFromResponse(request))
    path = os.path.join(tmpDir, filename)

    total = 0
    maxSize = spec.get('maxSize')

    with open(path, 'wb') as out:
        for buf in request.iter_content(32768):
            length = len(buf)
            if maxSize and length + total > maxSize:
                raise Exception('Exceeded max download size of {} bytes.'
                                .format(maxSize))
            out.write(buf)
            total += length

    return path
