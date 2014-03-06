import celery
import cherrypy
import json
from celery.result import AsyncResult
from girder import events
from StringIO import StringIO
from girder.constants import AccessType


celeryapp = celery.Celery('cardoon',
    backend='mongodb://localhost/cardoon',
    broker='mongodb://localhost/cardoon')

def getItemContent(itemId, itemApi):
    user = itemApi.getCurrentUser()

    item = itemApi.getObjectById(itemApi.model('item'), id=itemId,
        checkAccess=True, user=user,
        level=AccessType.READ)  # Access Check
    files = [file for file in itemApi.model('item').childFiles(item=item)]

    if len(files) > 1:
        raise Exception('Expected one file for running an analysis')

    stream = itemApi.model('file').download(files[0], headers=False)()
    io = StringIO()
    for chunk in stream:
        io.write(chunk)
    return io.getvalue()

def load(info):
    def cardoonItemGet(event):
        path = event.info['pathParams']
        if len(path) >= 5 and path[1] == 'cardoon':
            itemId = path[0]
            inputType = path[2]
            inputFormat = path[3]
            outputFormat = path[4]
            itemApi = info['apiRoot'].item

            content = getItemContent(itemId, itemApi)

            asyncResult = celeryapp.send_task('cardoon.convert', [inputType,
                {"data": content, "format": inputFormat},
                {"format": outputFormat}
            ])

            result = asyncResult.get()
            event.addResponse(result)
            event.stopPropagation()
            event.preventDefault()
        if len(path) >= 4 and path[1] == 'cardoon':
            itemId = path[0]
            jobId = path[2]
            operation = path[3]
            job = AsyncResult(jobId, backend=celeryapp.backend)
            if operation == 'status':
                response = {'status': job.state}
                if job.state == celery.states.FAILURE:
                    response['message'] = str(job.result)
                elif job.state == 'PROGRESS':
                    response['meta'] = str(job.result)
                event.addResponse(response)
                event.stopPropagation()
                event.preventDefault()
            elif operation == 'result':
                response = {'result': job.result}
                event.addResponse(response)
                event.stopPropagation()
                event.preventDefault()

    def cardoonItemPost(event):
        path = event.info['pathParams']
        if len(path) >= 2 and path[1] == 'cardoon':
            try:
                params = json.load(cherrypy.request.body)
                itemId = path[0]
                itemApi = info['apiRoot'].ite

                content = getItemContent(itemId, itemApi)

                analysis = json.loads(content)
                asyncResult = celeryapp.send_task('cardoon.run', [analysis], params)
                event.addResponse({'id': asyncResult.task_id})
                event.stopPropagation()
                event.preventDefault()

            except:
                import traceback, sys
                traceback.print_exc(file=sys.stdout)

    def cardoonItemDelete(event):
        if len(path) >= 3 and path[1] == 'cardoon':
            jobId = path[2]
            task = AsyncResult(jobId, backend=celeryapp.backend)
            task.revoke(celeryapp.broker_connection(), terminate=True)
            event.addResponse({'status': job.state})
            event.stopPropagation()
            event.preventDefault()

    events.bind('rest.item.get.before', 'cardoon', cardoonItemGet)
    events.bind('rest.item.post.before', 'cardoon', cardoonItemPost)
    events.bind('rest.item.delete.before', 'cardoon', cardoonItemDelete)
