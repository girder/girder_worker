import girder_client
import json
import os
from girder_worker import config
from six import StringIO

# Make a sensible limit for metadata outputs
MAX_METADATA_LENGTH = 4 * 1024 * 1024  # 4MB


def _get_cache_settings(spec):
    if not spec.get('use_cache', True):
        return None
    if not config.getboolean('girder_io', 'diskcache_enabled'):
        return None
    return dict(
        directory=config.get('girder_io', 'diskcache_directory'),
        eviction_policy=config.get('girder_io', 'diskcache_eviction_policy'),
        size_limit=config.getint('girder_io', 'diskcache_size_limit'),
        cull_limit=config.getint('girder_io', 'diskcache_cull_limit'),
        large_value_threshold=config.getint(
            'girder_io', 'diskcache_large_value_threshold'),
    )


def _init_client(spec, require_token=False):
    if 'api_url' in spec:
        client = girder_client.GirderClient(
            apiUrl=spec['api_url'],
            cacheSettings=_get_cache_settings(spec))
    elif 'host' in spec:
        scheme = spec.get('scheme', 'http')
        port = spec.get('port', {
            'http': 80,
            'https': 443
        }[scheme])
        api_root = spec.get('api_root', '/api/v1')
        client = girder_client.GirderClient(
            host=spec['host'], scheme=scheme, apiRoot=api_root, port=port,
            cacheSettings=_get_cache_settings(spec))
    else:
        raise Exception('You must pass either an api_url or host key for '
                        'Girder input and output bindings.')

    if 'token' in spec:
        client.setToken(spec['token'])
    elif require_token:
        raise Exception('You must pass a token for Girder authentication.')

    return client


def _fetch_parent_item(file_id, client, dest):
    """
    Fetches the whole item that contains the given file ID into the given
    destination directory. Returns the path to the specific file once the
    download is complete.
    """
    target_file = client.getResource('file', file_id)
    item = client.getResource('item', target_file['itemId'])
    dest = os.path.join(dest, client.transformFilename(item['name']))
    target_path = dest

    for file in client.listFile(item['_id']):
        path = os.path.join(dest, client.transformFilename(file['name']))
        client.downloadFile(file['_id'], path)

        if file['_id'] == target_file['_id']:
            target_path = path

    return target_path


def fetch_handler(spec, **kwargs):
    resource_type = spec.get('resource_type', 'file').lower()
    task_input = kwargs.get('task_input', {})
    target = task_input.get('target', 'filepath')
    fetch_parent = spec.get('fetch_parent', False)
    direct_path = spec.get('direct_path')

    if 'id' not in spec:
        raise Exception('Must pass a resource ID for girder inputs.')
    if 'name' not in spec:
        raise Exception('Must pass a name for girder inputs.')

    client = _init_client(spec)
    filename = client.transformFilename(spec['name'])
    dest = os.path.join(kwargs['_tempdir'], filename)

    if resource_type == 'folder':
        client.downloadFolderRecursive(spec['id'], dest)
    elif resource_type == 'item':
        client.downloadItem(spec['id'], kwargs['_tempdir'], filename)
    elif resource_type == 'file':
        if fetch_parent:
            # If we fetch the parent, we can't use direct paths as the
            # task may needs all of the siblings next to each other
            dest = _fetch_parent_item(spec['id'], client, kwargs['_tempdir'])
        elif (direct_path and config.getboolean('girder_io', 'allow_direct_path') and
                os.path.isfile(direct_path)):
            # If the specification includes a direct path AND it is allowed by
            # the worker configuration AND it is a reachable file, use it.
            dest = direct_path
        else:
            client.downloadFile(spec['id'], dest)
    else:
        raise Exception('Invalid resource type: ' + resource_type)

    if target == 'filepath':
        return dest
    elif target == 'memory':
        with open(dest, 'rb') as fd:
            return fd.read()
    else:
        raise Exception('Invalid Girder push target: ' + target)


def _require_name(name, spec):
    if not name and not spec.get('name'):
        raise Exception('Girder output missing "name" field.')
    return name or spec['name']


def _send_to_girder(client, spec, stream, size, reference, name=None):
    """
    Send an output to Girder as either a file or as metadata on an item
    or folder.

    :param client: The Girder client.
    :param spec: The output binding.
    :param stream: The stream holding the contents of the output data.
    :param size: Size in bytes of the output data
    :param reference: Arbitrary reference string to be passed to the server.
    :param name: Name of the created resource (not required for metadata outputs).
    """
    if spec.get('as_metadata') is True:
        if size > MAX_METADATA_LENGTH:
            raise Exception('Girder metadata output too large (%s bytes).' % size)

        try:
            obj = json.load(stream)
        except (ValueError, TypeError):
            raise Exception('Invalid JSON for metadata output')

        if not isinstance(obj, dict):
            raise Exception('Output must be a JSON Object (got type %s).' % type(obj))

        if 'parent_id' in spec:
            # We need to create a new item and attach this metadata to it
            name = _require_name(name, spec)
            itemId = client.createItem(parentFolderId=spec['parent_id'], name=name)['_id']
            client.addMetadataToItem(itemId, obj)
        elif 'item_id' in spec:
            # We need to attach this as metadata on an existing resource
            client.addMetadataToItem(spec['item_id'], obj)
        else:
            raise Exception('Girder metadata outputs require a parent_id or item_id.')
    else:
        if 'parent_id' not in spec:
            raise Exception('Must pass parent ID for Girder file outputs.')

        name = _require_name(name, spec)

        parent_type = spec.get('parent_type', 'folder')
        file = client.uploadFile(
            parentId=spec['parent_id'], stream=stream, size=size, parentType=parent_type,
            name=name, reference=reference)

        if 'metadata' in spec:
            client.addMetadataToItem(file['itemId'], spec['metadata'])


def push_handler(data, spec, **kwargs):
    reference = spec.get('reference')

    if reference is None:
        # Check for reference in the job manager if none in the output spec
        reference = getattr(kwargs.get('_job_manager'), 'reference', None)

    task_output = kwargs.get('task_output', {})
    target = task_output.get('target', 'filepath')

    client = _init_client(spec, require_token=True)

    if target == 'memory':
        _send_to_girder(
            client=client, spec=spec, stream=StringIO(data), size=len(data), reference=reference)
    elif target == 'filepath':
        name = spec.get('name') or os.path.basename(data)
        if os.path.isdir(data):
            if spec['parent_type'] == 'item':
                for f in os.listdir(data):
                    path = os.path.join(data, f)
                    if os.path.isfile(path):
                        client.uploadFileToItem(spec['parent_id'], path, reference=reference)
            else:
                client.upload(data, spec['parent_id'], spec['parent_type'], reference=reference)
        else:
            size = os.path.getsize(data)
            with open(data, 'rb') as fd:
                _send_to_girder(
                    client=client, spec=spec, stream=fd, size=size, reference=reference, name=name)
    else:
        raise Exception('Invalid Girder push target: ' + target)


def load(params):
    from girder_worker.core import io
    io.register_fetch_handler('girder', fetch_handler)
    io.register_push_handler('girder', push_handler)
