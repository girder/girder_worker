from __future__ import absolute_import

from . import http, local, mongodb


def _detectMode(spec):
    mode = spec.get('mode', 'auto')

    if mode == 'auto':
        # We guess the mode based on the "url" value
        if 'url' not in spec:
            raise Exception('IO mode "auto" requires a "url" field.')
        scheme = spec['url'].split(':', 1)[0]

        if scheme == 'https':
            mode = 'http'
        elif scheme == 'file':
            mode = 'local'
            spec['path'] = spec['url'][7:]  # Truncate "file://"
        else:
            mode = scheme

    return mode


def fetch(spec, **kwargs):
    """
    This function can be called on any valid input binding specification and is
    responsible for performing any operations necessary to fetch the data. Once
    any fetch operations are complete, this returns the value to which the
    corresponding variable should be set.

    :param input_spec: The specification of the input to fetch. This is a
        LOCATION_SPEC type in the Romanesco grammar.
    :type input_spec: dict
    """
    mode = _detectMode(spec)

    if mode == 'http':
        return http.fetch(spec, **kwargs)
    elif mode == 'mongodb':
        return mongodb.fetch(spec, **kwargs)
    elif mode == 'local':
        return local.fetch(spec, **kwargs)
    elif mode == 'inline':
        return spec['data']
    else:
        raise Exception('Unknown input fetch mode: ' + mode)


def push(data, spec, **kwargs):
    """
    The opposite of fetch, this is responsible for writing data to some
    destination in a specified mode defined by ``spec``.

    :param data: The data to push
    :type data: opaque
    :param spec: The output spec
    :type spec: dict
    """
    mode = _detectMode(spec)

    if mode == 'http':
        return http.push(data, spec, **kwargs)
    elif mode == 'mongodb':
        return mongodb.push(data, spec, **kwargs)
    elif mode == 'local':
        return local.push(data, spec, **kwargs)
    else:
        raise Exception('Unknown output push mode: ' + mode)
