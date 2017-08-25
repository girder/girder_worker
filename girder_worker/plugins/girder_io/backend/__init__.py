from celery.backends.base import BaseBackend
from celery.exceptions import ImproperlyConfigured
from celery import states
from girder_client import GirderClient, HttpError
try:
    from urllib.parse import parse_qsl, urlparse
except ImportError:
    from urlparse import urlparse, parse_qsl
import json
from datetime import datetime
import pytz


class GirderBackend(BaseBackend):
    """The Girder result backend."""

    def __init__(self, app, url=None,
                 api_key=None,
                 token=None,
                 parent_id=None,
                 parent_type=None, **kwargs):
        super(GirderBackend, self).__init__(app, url=url,  **kwargs)

        self._girder = None
        if not self._in_girder:
            # If we are outside Girder we need a url
            if self.url is None:
                raise ImproperlyConfigured(
                        'url for Girder server must be provided.')

        self._token = token
        self._api_key = api_key
        self._parent_id = parent_id
        self._parent_type = parent_type
        self._gclient = None

        parts = urlparse(url)
        query_params = dict(parse_qsl(parts.query))

        # Give precedence to parameter passed in
        if self._token is None:
            self._token = query_params.get('token')

        if self._api_key is None:
            self._api_key = query_params.get('apiKey')

        if self._parent_id is None:
            self._parent_id = query_params.get('parentId')

        if self._parent_type is None:
            self._parent_type = query_params.get('parentType')

        self.url = '%s://%s:%s/api/v1' % (parts.scheme, parts.hostname, parts.port)

        if self._api_key is None and self._token is None:
            raise ImproperlyConfigured(
                'An API key or token for Girder must be provided.')

        if self._parent_id is None or self._parent_type is None:
            raise ImproperlyConfigured(
                'A parent resource must be provided.')

    @property
    def _in_girder(self):
        if self._girder is None:
            self._girder = False
            try:
                from girder.utility.model_importer import ModelImporter
                self._girder = True
            except ImportError:
                pass

        return self._girder

    @property
    def _client(self):
        if self._gclient is None:
            self._gclient = GirderClient(apiUrl=self.url)
            if self._api_key:
                self._gclient.authenticate(apiKey=self._api_key)
            else:
                self._gclient.token = self._token

        return self._gclient

    def _store_result(self, task_id, result, state,
                      traceback=None, request=None, **kwargs):

        client = self._client

        # If the request has an url and token use these
        if hasattr(request, 'girder_api_url') and hasattr(request, 'girder_client_token'):
            client = GirderClient(apiUrl=request.girder_api_url)
            client.token = request.girder_client_token

        result_meta = {
            'status': state,
            'result': result,
            'timestamp': datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat(),
            'traceback': self.encode(traceback),
            'children': self.encode(
                self.current_task_children(request),
            )
        }

        if self._parent_type == 'folder':
            # Change to one call then PR is merged into master
            item = self._client.createItem(self._parent_id, task_id, reuseExisting=False)
            self._client.addMetadataToItem(item['_id'], result_meta)

        return result

    def _forget_girder(self, task_id):
        from girder.utility.model_importer import ModelImporter
        from girder.api.rest import getCurrentUser
        from girder.constants import AccessType
        folder = ModelImporter.model('folder').load(
                id=self._parent_id, user=getCurrentUser(), level=AccessType.ADMIN)

        filters = {
            'name': task_id
        }
        items = list(ModelImporter.model('folder').childItems(
                     folder=folder, limit=1, filters=filters))

        if len(items) == 1:
            item = items[0]
            ModelImporter.model('item').remove(item)

    def _forget_girder_client(self, task_id):
        items = list(self._client.listItem(self._parent_id, name=task_id, limit=1))
        if len(items) == 1:
            item = items[0]
            self._client.delete('item/%s' % item['_id'])

    def _forget(self, task_id):
        if self._in_girder:
            self._forget_girder(task_id)
        else:
            self._forget_girder_client(task_id)

    def _group_meta(self, result):
        return {
            'result': [i.id for i in result],
            'timestamp': datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat()
        }

    def _save_group_girder(self, group_id, result):
        from girder.utility.model_importer import ModelImporter
        from girder.api.rest import getCurrentUser
        from girder.constants import AccessType
        folder = ModelImporter.model('folder').load(
                id=self._parent_id, user=getCurrentUser(), level=AccessType.WRITE)

        item_model = ModelImporter.model('item')
        item = item_model.createItem(group_id, getCurrentUser(),
                                     folder)
        item_model.setMetadata(item, self._group_meta(result))

        return result

    def _save_group_girder_client(self, group_id, result):
        group_meta = self._group_meta(result)
        # Change to one call then PR is merged into master
        item = self._client.createItem(self._parent_id, group_id, reuseExisting=False)
        self._client.addMetadataToItem(item['_id'], group_meta)

        return result

    def _save_group(self, group_id, result):
        if self._in_girder:
            return self._save_group_girder(group_id, result)
        else:
            return self._save_group_girder_client(group_id, result)

    def _delete_group(self, group_id):
        self._forget(group_id)

    def _task_meta_from_item(self, item):
        print(item)
        meta = item['meta']

        return self.meta_from_decoded({
            'task_id': item['name'],
            'status': meta['status'],
            'result': meta['result'],
            'timestamp': meta['timestamp'],
            'traceback': self.decode(meta['traceback']),
            'children': self.decode(meta['children']),
        })

    def _get_task_meta_for_girder(self, task_id):
        from girder.utility.model_importer import ModelImporter
        from girder.api.rest import getCurrentUser
        from girder.constants import AccessType
        folder = ModelImporter.model('folder').load(
                id=self._parent_id, user=getCurrentUser(), level=AccessType.READ)

        filters = {
            'name': task_id
        }
        items = list(ModelImporter.model('folder').childItems(
                     folder=folder, limit=1, filters=filters))

        if len(items) == 1:
            item = items[0]
            return self._task_meta_from_item(item)

        return {'status': states.PENDING, 'result': None}

    def _get_task_meta_for_girder_client(self, task_id):
        items = list(self._client.listItem(self._parent_id, name=task_id, limit=1))
        if len(items) == 1:
            item = items[0]

            return self._task_meta_from_item(item)

        return {'status': states.PENDING, 'result': None}

    def _get_task_meta_for(self, task_id):
        if self._in_girder:
            return self._get_task_meta_for_girder(task_id)
        else:
            return self._get_task_meta_for_girder_client(task_id)

    def _group_meta_from_item(self, item):
        meta = item['meta']

        return {
            'task_id': item['name'],
            'timestamp': meta['timestamp'],
            'result': [
                self.app.AsyncResult(task)
                for task in meta['result']
                ],
        }

    def _restore_group_girder(self, group_id):
        from girder.utility.model_importer import ModelImporter
        from girder.api.rest import getCurrentUser
        from girder.constants import AccessType
        folder = ModelImporter.model('folder').load(
                id=self._parent_id, user=getCurrentUser(), level=AccessType.READ)

        filters = {
            'name': group_id
        }
        items = list(ModelImporter.model('folder').childItems(
                     folder=folder, limit=1, filters=filters))

        if len(items) == 1:
            item = items[0]
            return self._group_meta_from_item(item)

        return {'status': states.PENDING, 'result': None}

    def _restore_group_grider_client(self, group_id):
        items = list(self._client.listItem(self._parent_id, name=group_id, limit=1))
        if len(items) == 1:
            item = items[0]

            return self._group_meta_from_item(item)

        return {'status': states.PENDING, 'result': None}

    def _restore_group(self, group_id):
        if self._in_girder:
            return self._restore_group_girder(group_id)
        else:
            return self._restore_group_girder_client(group_id)
