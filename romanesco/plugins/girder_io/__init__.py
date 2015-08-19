import girder_client
import os
import romanesco


def _init_client(spec, require_token=False):
    if 'host' not in spec:
        raise Exception('Host key required for girder fetch mode')

    scheme = spec.get('scheme', 'http')
    port = spec.get('port', {
        'http': 80,
        'https': 443
    }[scheme])
    api_root = spec.get('apiRoot', '/api/v1')
    client = girder_client.GirderClient(
        host=spec['host'], scheme=scheme, apiRoot=api_root, port=port)

    if 'token' in spec:
        client.token = spec['token']
    elif require_token:
        raise Exception('You must pass a token for girder authentication.')

    return client


def fetch_handler(spec, **kwargs):
    resource_type = spec.get('resourceType', 'file').lower()

    if 'id' not in spec:
        raise Exception('Must pass a resource ID for girder inputs.')
    if 'name' not in spec:
        raise Exception('Must pass a name for girder inputs.')

    client = _init_client(spec)
    dest = os.path.join(kwargs['_tmp_dir'], spec['name'])

    if resource_type == 'folder':
        client.downloadFolderRecursive(spec['id'], dest)
    elif resource_type == 'item':
        client.downloadItem(spec['id'], kwargs['_tmp_dir'], spec['name'])
    elif resource_type == 'file':
        client.downloadFile(spec['id'], dest)
    else:
        raise Exception('Invalid resourceType: ' + resource_type)

    return dest


def push_handler(data, spec, **kwargs):
    parent_type = spec.get('parentType', 'folder')
    name = spec.get('name', os.path.basename(data))
    description = spec.get('description')

    if 'parentId' not in spec:
        raise Exception('Must pass parentId for girder outputs.')

    client = _init_client(spec, require_token=True)

    if parent_type == 'folder':
        item = client.createItem(
            spec['parentId'], name, description=description)
        client.uploadFileToItem(item['_id'], data)
    elif parent_type == 'item':
        client.uploadFileToItem(spec['parentId'], data)
    else:
        raise Exception('Invalid parentType: ' + parent_type)


def load(params):
    romanesco.io.register_fetch_handler('girder', fetch_handler)
    romanesco.io.register_push_handler('girder', push_handler)
