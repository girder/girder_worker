import bson
import celery
import cherrypy
import json
import sys
import time

from celery.result import AsyncResult
from StringIO import StringIO
from girder.constants import AccessType
import sys

from girder import events
from girder.api import access, rest
from girder.api.describe import Description
from girder.models.model_base import AccessException, ValidationException
from girder.utility.model_importer import ModelImporter
from girder.plugins.jobs.constants import JobStatus

# If you desire authorization to run analyses (strongly encouraged), make sure
# to specify so in the plugin settings page. By default, authorization control
# is disabled.

_celeryapp = None


class PluginSettings():
    BROKER = 'romanesco.broker'
    BACKEND = 'romanesco.backend'
    FULL_ACCESS_USERS = 'romanesco.full_access_users'
    REQUIRE_AUTH = 'romanesco.require_auth'
    SAFE_FOLDERS = 'romanesco.safe_folders'


def getCeleryApp():
    """
    Lazy loader for the celery app. Reloads anytime the settings are updated.
    """
    global _celeryapp

    if _celeryapp is None:
        settings = ModelImporter.model('setting')
        backend = settings.get(PluginSettings.BACKEND) or \
            'mongodb://localhost/romanesco'
        broker = settings.get(PluginSettings.BROKER) or \
            'mongodb://localhost/romanesco'
        _celeryapp = celery.Celery('romanesco', backend=backend, broker=broker)
    return _celeryapp


def schedule(event):
    """
    This is bound to the "jobs.schedule" event, and will be triggered any time
    a job is scheduled. This handler will process any job that has the
    handler field set to "romanesco_handler".
    """
    job = event.info
    if job['handler'] == 'romanesco_handler':
        # Stop event propagation since we have taken care of scheduling.
        event.stopPropagation()

        # Send the task to celery
        asyncResult = getCeleryApp().send_task(
            'romanesco.run', job['args'], job['kwargs'])

        # Set the job status to queued and record the task ID from celery.
        job['status'] = JobStatus.QUEUED
        job['taskId'] = asyncResult.task_id
        ModelImporter.model('job', 'jobs').save(job)


def validateSettings(event):
    """
    Handle plugin-specific system settings. Right now we don't do any
    validation for the broker or backend URL settings, but we do reinitialize
    the celery app object with the new values.
    """
    global _celeryapp
    key = event.info['key']
    val = event.info['value']

    if key == PluginSettings.BROKER:
        _celeryapp = None
        event.preventDefault()
    elif key == PluginSettings.BACKEND:
        _celeryapp = None
        event.preventDefault()
    elif key == PluginSettings.FULL_ACCESS_USERS:
        if not isinstance(val, (list, tuple)):
            raise ValidationException('Full access users must be a JSON list.')
        event.preventDefault()
    elif key == PluginSettings.REQUIRE_AUTH:
        if not isinstance(val, bool):
            raise ValidationException(
                'Require auth setting must be true or false.')
        event.preventDefault()
    elif key == PluginSettings.SAFE_FOLDERS:
        if not isinstance(val, (list, tuple)):
            raise ValidationException('Safe folders must be a JSON list.')
        event.preventDefault()


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
    @access.user
    @rest.boundHandler()
    def romanescoCreateModule(self, params):
        """Create a new romanesco module."""
        self.requireParams('name', params)

        user = self.getCurrentUser()
        public = self.boolParam('public', params, default=False)

        collection = self.model('collection').createCollection(
            name=params['name'], description=params.get('description'),
            public=public, creator=user)

        for name in ('Data', 'Analyses', 'Visualizations'):
            folder = self.model('folder').createFolder(
                name=name, public=public, parentType='collection',
                parent=collection, creator=user)

        return self.model('collection').filter(collection, user=user)

    @access.public
    def romanescoConvertData(inputType, inputFormat, outputFormat, params):
        content = cherrypy.request.body.read()

        asyncResult = getCeleryApp().send_task('romanesco.convert', [
            inputType,
            {"data": content, "format": inputFormat},
            {"format": outputFormat}
        ])

        return asyncResult.get()

    @access.public
    def romanescoConvert(itemId, inputType, inputFormat, outputFormat, params):
        itemApi = info['apiRoot'].item

        content = getItemContent(itemId, itemApi)

        asyncResult = getCeleryApp().send_task('romanesco.convert', [
            inputType,
            {"data": content, "format": inputFormat},
            {"format": outputFormat}
        ])

        return asyncResult.get()

    @access.public
    def getTaskId(jobId):
        # Get the celery task ID for this job.
        jobApi = info['apiRoot'].job
        job = jobApi.model('job', 'jobs').load(
            jobId, user=jobApi.getCurrentUser(), level=AccessType.READ)
        return job["taskId"]

    @access.public
    def romanescoRunStatus(itemId, jobId, params):
        taskId = getTaskId(jobId)

        # Get the celery result for the corresponding task ID.
        result = AsyncResult(taskId, backend=getCeleryApp().backend)
        try:
            response = {'status': result.state}
            if result.state == celery.states.FAILURE:
                response['message'] = str(result.result)
            elif result.state == 'PROGRESS':
                response['meta'] = str(result.result)
            return response
        except Exception:
            return {
                'status': 'FAILURE',
                'message': sys.exc_info(),
                'trace': sys.exc_info()[2]
            }
    romanescoRunStatus.description = (
        Description('Show the status of a romanesco task')
        .param('jobId', 'The job ID for this task.', paramType='path')
        .param('itemId', 'Not used.', paramType='path'))


    @access.public
    def romanescoRunResult(itemId, jobId, params):
        taskId = getTaskId(jobId)
        job = AsyncResult(taskId, backend=getCeleryApp().backend)
        return {'result': job.result}
    romanescoRunResult.description = (
        Description('Show the final output of a romanesco task.')
        .param('jobId', 'The job ID for this task.', paramType='path')
        .param('itemId', 'Not used.', paramType='path'))

    @access.public
    def romanescoRunOutput(itemId, jobId, params):
        jobApi = info['apiRoot'].job
        taskId = getTaskId(jobId)
        timeout = 300
        cherrypy.response.headers['Content-Type'] = 'text/event-stream'
        cherrypy.response.headers['Cache-Control'] = 'no-cache'

        def sseMessage(output):
            if type(output) == unicode:
                output = output.encode('utf8')
            return 'event: log\ndata: {}\n\n'.format(output)

        def streamGen():
            start = time.time()
            endtime = None
            oldLog = ''
            while (time.time() - start < timeout
                    and cherrypy.engine.state == cherrypy.engine.states.STARTED
                    and (endtime is None or time.time() < endtime)):
                # Display new log info from this job since the
                # last execution of this loop.
                job = jobApi.model('job', 'jobs').load(
                    jobId,
                    user=jobApi.getCurrentUser(),
                    level=AccessType.READ)
                newLog = job['log']
                if newLog != oldLog:
                    start = time.time()
                    logDiff = newLog[newLog.find(oldLog) + len(oldLog):]
                    oldLog = newLog
                    # We send a separate message for each line,
                    # as I discovered that any information after the
                    # first newline was being lost...
                    for line in logDiff.rstrip().split('\n'):
                        yield sseMessage(line)
                if endtime is None:
                    result = AsyncResult(taskId,
                                         backend=getCeleryApp().backend)
                    if (result.state == celery.states.FAILURE or
                            result.state == celery.states.SUCCESS or
                            result.state == celery.states.REVOKED):
                        # Stop checking for messages in 5 seconds
                        endtime = time.time() + 5
                time.sleep(0.5)

            # Signal the end of the stream
            yield 'event: eof\ndata: null\n\n'

            # One more for good measure - client should not get this
            yield 'event: past-end\ndata: null\n\n'

        return streamGen
    romanescoRunOutput.description = (
        Description('Show the output for a romanesco task.')
        .param('jobId', 'The job ID for this task.', paramType='path')
        .param('itemId', 'Not used.', paramType='path'))

    @access.public
    @rest.boundHandler(info['apiRoot'].item)
    @rest.loadmodel(map={'itemId': 'item'}, model='item',
                    level=AccessType.READ)
    def romanescoRun(self, item, params):
        # Make sure that we have permission to perform this analysis.
        user = self.getCurrentUser()

        settings = ModelImporter.model('setting')
        requireAuth = settings.get(PluginSettings.REQUIRE_AUTH, True)

        if requireAuth:
            fullAccessUsers = settings.get(PluginSettings.FULL_ACCESS_USERS, ())
            safeFolders = settings.get(PluginSettings.SAFE_FOLDERS, ())

            if (str(item['folderId']) not in safeFolders and (
                    not user or user['login'] not in fullAccessUsers)):
                raise AccessException('Unauthorized user.')

        analysis = item.get('meta', {}).get('analysis')

        if type(analysis) is not dict:
            raise rest.RestException(
                'Must specify a valid JSON object as the "analysis" metadata '
                'field on the input item.')

        # Create the job record.
        jobModel = self.model('job', 'jobs')
        public = False
        if user is None:
            public = True
        job = jobModel.createJob(
            title=analysis['name'], type='romanesco_task',
            handler='romanesco_handler', user=user, public=public)

        # Create a token that is scoped for updating the job.
        jobToken = jobModel.createJobToken(job)

        # Get the analysis parameters (includes inputs & outputs).
        try:
            kwargs = json.load(cherrypy.request.body)
        except ValueError:
            raise rest.RestException(
                'You must pass a valid JSON object in the request body.')

        apiUrl = cherrypy.url().rsplit('/', 3)[0]

        # These parameters are used to get stdout/stderr back from Celery
        # to Girder.
        kwargs['jobInfo'] = {
            'url': '{}/job/{}'.format(apiUrl, job['_id']),
            'method': 'PUT',
            'headers': {'Girder-Token': jobToken['_id']},
            'logPrint': True
        }

        job['kwargs'] = kwargs
        job['args'] = [analysis]
        job = jobModel.save(job)

        # Schedule the job (triggers the schedule method above)
        jobModel.scheduleJob(job)
        return jobModel.filter(job, user)
    romanescoRun.description = (
        Description('Run a task specified by item metadata.')
        .param('itemId', 'The item containing the analysis as metadata.',
               paramType='path')
        .param('kwargs', 'Additional kwargs for the worker task.',
               paramType='body'))

    @access.public
    def romanescoStopRun(jobId, params):
        task = AsyncResult(jobId, backend=getCeleryApp().backend)
        task.revoke(getCeleryApp().broker_connection(), terminate=True)
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
        'GET',
        (':itemId', 'romanesco', ':jobId', 'output'),
        romanescoRunOutput)

    info['apiRoot'].item.route(
        'POST',
        (':itemId', 'romanesco'),
        romanescoRun)

    info['apiRoot'].item.route(
        'DELETE',
        (':itemId', 'romanesco', ':jobId'),
        romanescoStopRun)

    events.bind('jobs.schedule', 'romanesco', schedule)
    events.bind('model.setting.validate', 'romanesco', validateSettings)
