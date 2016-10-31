from __future__ import absolute_import
from . import http, local, mongodb

import os
import tempfile

_fetch_map = {}
_push_map = {}
_stream_fetch_map = {}
_stream_push_map = {}


def _inline_fetch(spec, **kwargs):
    taskInput = kwargs.get('task_input', {})
    target = taskInput.get('target', 'memory')
    if target == 'filepath':
        # Ensure we have a trailing slash
        tmpDir = os.path.join(kwargs['_tempdir'], '')

        if 'filename' in taskInput:
            filename = taskInput['filename']
            path = os.path.join(tmpDir, filename)
            with open(path, 'wb') as out:
                out.write(spec['data'])
        else:
            with tempfile.NamedTemporaryFile(
                    'wb', prefix=tmpDir, delete=False) as out:
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


def register_stream_fetch_adapter(mode, adapter_cls):
    """
    Register an adapter class to handle streaming input for a given mode.

    :param mode: The mode to bind this adapter to.
    :type mode: str
    :param adapter_cls: The adapter class that will be instantiated to handle
        stream fetching for the given mode.
    :type adapter_cls: :py:class:`StreamFetchAdapter`
    """
    _stream_fetch_map[mode] = adapter_cls


def register_stream_push_adapter(mode, adapter_cls):
    """
    Register an adapter class to handle stream pushing for a given mode.

    :param mode: The mode to bind this adapter to.
    :type mode: str
    :param adapter_cls: The adapter class that will be instantiated to handle
        stream pushing for the given mode.
    :type adapter_cls: :py:class:`StreamPushAdapter`
    """
    _stream_push_map[mode] = adapter_cls


def _detect_mode(spec):
    mode = spec.get('mode', 'auto')

    if mode == 'auto':
        # We guess the mode based on the "url" value
        if 'url' not in spec:
            return 'inline'

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
        LOCATION_SPEC type in the grammar.
    :type input_spec: dict
    """
    mode = _detect_mode(spec)

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
    mode = _detect_mode(spec)

    if mode not in _push_map:
        raise Exception('Unknown output push mode: ' + mode)

    return _push_map[mode](data, spec, **kwargs)


def make_stream_fetch_adapter(input):
    """
    Create a stream fetch adapter based on the given input binding.
    """
    mode = _detect_mode(input)

    if mode not in _stream_fetch_map:
        raise Exception('Unknown streaming input fetch mode: ' + mode)

    return _stream_fetch_map[mode](input)


def make_stream_push_adapter(output):
    """
    Create a stream push adapter based on the given output binding.
    """
    mode = _detect_mode(output)

    if mode not in _stream_push_map:
        raise Exception('Unknown streaming output push mode: ' + mode)

    return _stream_push_map[mode](output)


register_fetch_handler('http', http.fetch)
register_fetch_handler('mongodb', mongodb.fetch)
register_fetch_handler('local', local.fetch)
register_fetch_handler('inline', _inline_fetch)


register_push_handler('http', http.push)
register_push_handler('mongodb', mongodb.push)
register_push_handler('local', local.push)
register_push_handler('inline', _inline_push)

register_stream_push_adapter('http', http.HttpStreamPushAdapter)
register_stream_fetch_adapter('http', http.HttpStreamFetchAdapter)
