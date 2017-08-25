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
        print(query_params)
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

        result_meta = {
            'status': state,
            'result': self.encode(result),
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

    def _forget(self, task_id):
        items = list(self._client.listItem(self._parent_id, name=task_id, limit=1))
        if len(items) == 1:
            item = items[0]
            self._client.delete('item/%s' % item['_id'])


    def _save_group(self, group_id, result):
        print('save group')
        group_meta = {
            'result': self.encode([i.id for i in result]),
            'timestamp': datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat()
        }

        if self._parent_type == 'folder':
            # Change to one call then PR is merged into master
            item = self._client.createItem(self._parent_id, group_id, reuseExisting=False)
            self._client.addMetadataToItem(item['_id'], group_meta)

        return result

    def _delete_group(self, group_id):
        self._forget(group_id)

    def _get_task_meta_for(self, task_id):
        items = list(self._client.listItem(self._parent_id, name=task_id, limit=1))
        if len(items) == 1:
            item = items[0]
            meta = item['meta']

            return self.meta_from_decoded({
                'task_id': item['name'],
                'status': meta['status'],
                'result': self.decode(meta['result']),
                'timestamp': meta['timestamp'],
                'traceback': self.decode(meta['traceback']),
                'children': self.decode(meta['children']),
            })

        return {'status': states.PENDING, 'result': None}

    def _restore_group(self, group_id):
        items = list(self._client.listItem(self._parent_id, name=group_id, limit=1))
        if len(items) == 1:
            item = items[0]
            meta = item['meta']

            return {
                'task_id': item['name'],
                'timestamp': meta['timestamp'],
                'result': [
                    self.app.AsyncResult(task)
                    for task in self.decode(meta['result'])
                ],
            }
