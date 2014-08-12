import bson
import celery
import cherrypy
import json
from celery.result import AsyncResult
from StringIO import StringIO
from girder.constants import AccessType
import sys

# If you desire authentication to run analyses (strongly encouraged),
# Add the following to the girder config file:
#
# [romanesco]
#
# # Default is false, set to True to disallow free-for-all analysis execution
# # and limit execution to the user and folder white lists below.
# # require_auth: True
#
# # Whitelisted users who can run any analysis.
# # full_access_users: ["user1", "user2"]
#
# # Whitelisted folders where any user (including those not logged in)
# # can run analyses defined in these folders.
# # safe_folders: [bson.objectid.ObjectId("5314be7cea33db24b6aa490c")]


def getItemMetadata(itemId, itemApi):
    user = itemApi.getCurrentUser()
    item = itemApi.model('item').load(itemId, level=AccessType.READ, user=user)
    return item['meta']


def getParentFolder(itemId, itemApi):
    user = itemApi.getCurrentUser()
    item = itemApi.model('item').load(itemId, level=AccessType.READ, user=user)
    return item['folderId']


def getItemContent(itemId, itemApi):
    item = itemApi.getItem(id=itemId, params={})

    files = [file for file in itemApi.model('item').childFiles(item=item)]

    if len(files) > 1:
        raise Exception('Expected one file for running an analysis')

    stream = itemApi.model('file').download(files[0], headers=False)()
    io = StringIO()
    for chunk in stream:
        io.write(chunk)
    return io.getvalue()


def load(info):
    celeryapp = celery.Celery(
        'romanesco',
        backend='mongodb://localhost/romanesco',
        broker='mongodb://localhost/romanesco')

    def romanescoCreateModule(params):
        """Create a new romanesco module."""

        collectionApi = info['apiRoot'].collection

        collectionApi.requireParams(['name'], params)

        user = collectionApi.getCurrentUser()
        public = collectionApi.boolParam('public', params, default=False)

        collection = collectionApi.model('collection').createCollection(
            name=params['name'], description=params.get('description'),
            public=public, creator=user)

        folderApi = info['apiRoot'].folder

        folderApi.createFolder({
            'name': 'Data',
            'public': public,
            'parentType': 'collection',
            'parentId': collection['_id']})

        folderApi.createFolder({
            'name': 'Analyses',
            'public': public,
            'parentType': 'collection',
            'parentId': collection['_id']})

        return collectionApi.model('collection').filter(collection)

    def romanescoConvertData(inputType, inputFormat, outputFormat, params):
        content = cherrypy.request.body.read()

        asyncResult = celeryapp.send_task('romanesco.convert', [
            inputType,
            {"data": content, "format": inputFormat},
            {"format": outputFormat}
        ])

        return asyncResult.get()

    def romanescoConvert(itemId, inputType, inputFormat, outputFormat, params):
        itemApi = info['apiRoot'].item

        content = getItemContent(itemId, itemApi)

        asyncResult = celeryapp.send_task('romanesco.convert', [
            inputType,
            {"data": content, "format": inputFormat},
            {"format": outputFormat}
        ])

        return asyncResult.get()

    def romanescoRunStatus(itemId, jobId, params):
        job = AsyncResult(jobId, backend=celeryapp.backend)
        try:
            response = {'status': job.state}
            if job.state == celery.states.FAILURE:
                response['message'] = str(job.result)
            elif job.state == 'PROGRESS':
                response['meta'] = str(job.result)
            return response
        except Exception:
            return {
                'status': 'FAILURE',
                'message': sys.exc_info(),
                'trace': sys.exc_info()[2]
            }

    def romanescoRunResult(itemId, jobId, params):
        job = AsyncResult(jobId, backend=celeryapp.backend)
        return {'result': job.result}

    def romanescoRun(itemId, params):
        try:
            params = json.load(cherrypy.request.body)
            itemApi = info['apiRoot'].item
            user = itemApi.getCurrentUser()
            conf = info['config'].get('romanesco', {})
            requireAuth = conf.get('require_auth', False)
            fullAccessUsers = conf.get('full_access_users', [])
            safeFolders = conf.get('safe_folders', [])
            if (
                requireAuth
                and (not user or user['login'] not in fullAccessUsers)
                and getParentFolder(itemId, itemApi) not in safeFolders
            ):
                return {'error': 'Unauthorized'}

            metadata = getItemMetadata(itemId, itemApi)
            analysis = metadata["analysis"]

            asyncResult = celeryapp.send_task(
                'romanesco.run', [analysis], params)
            return {'id': asyncResult.task_id}

        except:
            return {
                'status': 'FAILURE',
                'message': sys.exc_info(),
                'trace': sys.exc_info()[2]
            }

    def romanescoStopRun(jobId, params):
        task = AsyncResult(jobId, backend=celeryapp.backend)
        task.revoke(celeryapp.broker_connection(), terminate=True)
        return {'status': task.state}

    info['apiRoot'].collection.route(
        'POST',
        ('romanesco', 'module'),
        romanescoCreateModule)

    info['apiRoot'].item.route(
        'POST',
        ('romanesco', ':inputType', ':inputFormat', ':outputFormat'),
        romanescoConvertData)

    info['apiRoot'].item.route(
        'GET',
        (':itemId', 'romanesco', ':inputType', ':inputFormat',
         ':outputFormat'),
        romanescoConvert)

    info['apiRoot'].item.route(
        'GET',
        (':itemId', 'romanesco', ':jobId', 'status'),
        romanescoRunStatus)

    info['apiRoot'].item.route(
        'GET',
        (':itemId', 'romanesco', ':jobId', 'result'),
        romanescoRunResult)

    info['apiRoot'].item.route(
        'POST',
        (':itemId', 'romanesco'),
        romanescoRun)

    info['apiRoot'].item.route(
        'DELETE',
        (':itemId', 'romanesco', ':jobId'),
        romanescoStopRun)
