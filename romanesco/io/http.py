import os
import re
import requests


def _readFilenameFromResponse(request, url):
    """
    This helper will derive a filename from the HTTP response, first attempting
    to use the content disposition header, otherwise falling back to the last
    token of the URL.
    """
    match = re.search('filename="(.*)"',
                      request.headers.get('Content-Disposition', ''))

    if match is None:
        return [t for t in url.split('/') if t][-1]
    else:
        return match.group(1)


def fetch(spec, **kwargs):
    """
    Downloads an input file via HTTP using requests.
    """
    tmpDir = kwargs['_tmp_dir']  # TODO create if not set?

    if 'url' not in spec:
        raise Exception('No URL specified for HTTP input.')

    url = spec['url']
    target = spec.get('target', 'file')
    method = getattr(requests, spec.get('method', 'get').lower())
    request = method(url, headers=spec.get('headers', {}), stream=True)

    try:
        request.raise_for_status()
    except:
        print 'HTTP fetch failed (%s). Response: %s' % (url, request.text)
        raise

    if target == 'file':
        if 'filename' in spec:
            filename = spec['filename']
        else:
            filename = _readFilenameFromResponse(request, url)

        path = os.path.join(tmpDir, filename)

        total = 0
        maxSize = spec.get('maxSize')

        with open(path, 'wb') as out:
            for buf in request.iter_content(65536):
                length = len(buf)
                if maxSize and length + total > maxSize:
                    raise Exception(
                        'Exceeded max download size of %d bytes.' % maxSize)
                out.write(buf)
                total += length

        return path
    elif target == 'memory':
        return ''.join(request.iter_content(65536))
    else:
        raise Exception('Invalid HTTP fetch target: ' + target)
