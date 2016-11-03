import girder_client
import os
from girder_worker import config
from six import StringIO


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
        client.token = spec['token']
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
            dest = _fetch_parent_item(spec['id'], client, kwargs['_tempdir'])
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


def push_handler(data, spec, **kwargs):
    reference = spec.get('reference')

    if reference is None:
        # Check for reference in the job manager if none in the output spec
        reference = getattr(kwargs.get('_job_manager'), 'reference', None)

    parent_type = spec.get('parent_type', 'folder')
    task_output = kwargs.get('task_output', {})
    target = task_output.get('target', 'filepath')

    if 'parent_id' not in spec:
        raise Exception('Must pass parent ID for girder outputs.')

    client = _init_client(spec, require_token=True)

    if target == 'memory':
        if not spec.get('name'):
            raise Exception('Girder uploads from memory objects must '
                            'explicitly pass a "name" field.')
        fd = StringIO(data)
        client.uploadFile(parentId=spec['parent_id'], stream=fd, size=len(data),
                          parentType=parent_type, name=spec['name'],
                          reference=reference)
    elif target == 'filepath':
        name = spec.get('name') or os.path.basename(data)
        size = os.path.getsize(data)
        with open(data, 'rb') as fd:
            client.uploadFile(parentId=spec['parent_id'], stream=fd, size=size,
                              parentType=parent_type, name=name,
                              reference=reference)
    else:
        raise Exception('Invalid Girder push target: ' + target)


def load(params):
    from girder_worker.core import io
    io.register_fetch_handler('girder', fetch_handler)
    io.register_push_handler('girder', push_handler)
