import celery
import cherrypy
import json
from celery.result import AsyncResult
from girder import events
from StringIO import StringIO
from girder.constants import AccessType
import sys
import traceback

celeryapp = celery.Celery('cardoon',
    backend='mongodb://localhost/cardoon',
    broker='mongodb://localhost/cardoon')

def getItemMetadata(itemId, itemApi):
    user = itemApi.getCurrentUser()
    item = itemApi.model('item').load(itemId, level=AccessType.READ, user=user)
    return item['meta']

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
    def cardoonConvertData(inputType, inputFormat, outputFormat, params):
        content = cherrypy.request.body.read()

        asyncResult = celeryapp.send_task('cardoon.convert', [inputType,
            {"data": content, "format": inputFormat},
            {"format": outputFormat}
        ])

        return asyncResult.get()

    def cardoonConvert(itemId, inputType, inputFormat, outputFormat, params):
        itemApi = info['apiRoot'].item

        content = getItemContent(itemId, itemApi)

        asyncResult = celeryapp.send_task('cardoon.convert', [inputType,
            {"data": content, "format": inputFormat},
            {"format": outputFormat}
        ])

        return asyncResult.get()

    def cardoonRunStatus(itemId, jobId, params):
        job = AsyncResult(jobId, backend=celeryapp.backend)
        try:
            response = {'status': job.state}
            if job.state == celery.states.FAILURE:
                response['message'] = str(job.result)
            elif job.state == 'PROGRESS':
                response['meta'] = str(job.result)
            return response
        except Exception:
            return {'status': 'FAILURE', 'message': sys.exc_info()}

    def cardoonRunResult(itemId, jobId, params):
        job = AsyncResult(jobId, backend=celeryapp.backend)
        return {'result': job.result}

    def cardoonRun(itemId, params):
        try:
            params = json.load(cherrypy.request.body)
            itemApi = info['apiRoot'].item

            metadata = getItemMetadata(itemId, itemApi)
            analysis = metadata["analysis"]

            asyncResult = celeryapp.send_task('cardoon.run', [analysis], params)
            return {'id': asyncResult.task_id}

        except:
            traceback.print_exc(file=sys.stdout)

    def cardoonStopRun(jobId, params):
        task = AsyncResult(jobId, backend=celeryapp.backend)
        task.revoke(celeryapp.broker_connection(), terminate=True)
        return {'status': job.state}

    info['apiRoot'].item.route('POST', ('cardoon', ':inputType', ':inputFormat', ':outputFormat'), cardoonConvertData)
    info['apiRoot'].item.route('GET', (':itemId', 'cardoon', ':inputType', ':inputFormat', ':outputFormat'), cardoonConvert)
    info['apiRoot'].item.route('GET', (':itemId', 'cardoon', ':jobId', 'status'), cardoonRunStatus)
    info['apiRoot'].item.route('GET', (':itemId', 'cardoon', ':jobId', 'result'), cardoonRunResult)
    info['apiRoot'].item.route('POST', (':itemId', 'cardoon'), cardoonRun)
    info['apiRoot'].item.route('DELETE', (':itemId', 'cardoon', ':jobId'), cardoonStopRun)
