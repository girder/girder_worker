from __future__ import absolute_import

from . import http, local, mongodb

import os
import tempfile

_fetch_map = {}
_push_map = {}


def _inline_fetch(spec, **kwargs):
    taskInput = kwargs.get('task_input', {})
    target = taskInput.get('target', 'memory')
    if target == 'filepath':
        tmpDir = kwargs['_tempdir']

        if 'filename' in taskInput:
            filename = taskInput['filename']
            path = os.path.join(tmpDir, filename)
            with open(path, 'wb') as out:
                out.write(spec['data'])
        else:
            with tempfile.NamedTemporaryFile('wb', prefix=tmpDir, delete=False) as out:
                out.write(spec['data'])
                path = out.name

        return path
    elif target == 'memory':
        return spec['data']
    else:
        raise Exception('Invalid fetch target: ' + target)


def _inline_push(data, spec, **kwargs):
    spec['data'] = data
    return spec


def register_fetch_handler(mode, handler):
    """
    Register a new handler function for fetching data for a given mode. This
    will override any existing handler mapped to the given mode.

    :param mode: The name of the mode this handler corresponds to.
    :type mode: str
    :param handler: The handler function that performs the fetch.
    :type handler: function
    """
    _fetch_map[mode] = handler


def register_push_handler(mode, handler):
    """
    Register a new handler function for pushing data for a given mode. This
    will override any existing handler mapped to the given mode.

    :param mode: The name of the mode this handler corresponds to.
    :type mode: str
    :param handler: The handler function that performs the data push.
    :type handler: function
    """
    _push_map[mode] = handler


def _detectMode(spec):
    mode = spec.get('mode', 'auto')

    if mode == 'auto':
        # We guess the mode based on the "url" value
        if 'url' not in spec:
            if 'data' in spec:
                return 'inline'

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

    if mode not in _fetch_map:
        raise Exception('Unknown input fetch mode: ' + mode)

    return _fetch_map[mode](spec, **kwargs)


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

    if mode not in _push_map:
        raise Exception('Unknown output push mode: ' + mode)

    return _push_map[mode](data, spec, **kwargs)


register_fetch_handler('http', http.fetch)
register_fetch_handler('mongodb', mongodb.fetch)
register_fetch_handler('local', local.fetch)
register_fetch_handler('inline', _inline_fetch)


register_push_handler('http', http.push)
register_push_handler('mongodb', mongodb.push)
register_push_handler('local', local.push)
register_push_handler('inline', _inline_push)
