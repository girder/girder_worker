import girder_worker
import traceback as tb
import celery
from celery import Celery, __version__
from distutils.version import LooseVersion
from celery.signals import (task_prerun, task_postrun,
                            task_failure, task_success,
                            worker_ready, before_task_publish)
from celery.result import AsyncResult
from six.moves import configparser
import sys
from .utils import JobStatus


class GirderAsyncResult(AsyncResult):
    def __init__(self, *args, **kwargs):
        self._job = None
        super(GirderAsyncResult, self).__init__(*args, **kwargs)

    @property
    def job(self):
        if self._job is None:
            try:
                # GirderAsyncResult() objects may be instantiated in either a girder REST
                # request,  or in some other context (e.g. from a running girder_worker
                # instance if there is a chain).  If we are in a REST request we should
                # have access to the girder package and can directly access the database
                # If we are in a girder_worker context (or even in python console or a
                # testing context) then we should get an ImportError and we can make a REST
                # request to get the information we need.
                from girder.utility.model_importer import ModelImporter
                job_model = ModelImporter.model('job', 'jobs')

                try:
                    return job_model.findOne({'celeryTaskId': self.task_id})
                except IndexError:
                    return None

            except ImportError:
                # Make a rest request to get the job info
                return None

        return self._job


class Task(celery.Task):
    """Girder Worker Task object"""

    _girder_job_title = '<unnamed job>'
    _girder_job_type = None
    _girder_job_public = False
    _girder_job_handler = 'celery_handler'
    _girder_job_other_fields = {}

    # These keys will be removed from apply_async's kwargs or options and
    # transfered into the headers of the message.
    special_headers = [
        'girder_client_token',
        'girder_api_url']

    # These keys will be available in the 'properties' dictionary inside
    # girder_before_task_publish() but will not be passed along in the message
    special_options = [
        'girder_user',
        'girder_job_title',
        'girder_job_type',
        'girder_job_public',
        'girder_job_handler',
        'girder_job_other_fields']

    def AsyncResult(self, task_id, **kwargs):
        return GirderAsyncResult(task_id, backend=self.backend,
                                 task_name=self.name, app=self.app, **kwargs)

    def apply_async(self, args=None, kwargs=None, task_id=None, producer=None,
                    link=None, link_error=None, shadow=None, **options):

        # Pass girder related job information through to
        # the signals by adding this information to options['headers']
        headers = {}

        # Certain keys may show up in either kwargs (e.g. via .delay(girder_token='foo')
        # or in options (e.g.  .apply_async(args=(), kwargs={}, girder_token='foo')
        # For those special headers,  pop them out of kwargs or options and put them
        # in headers so they can be picked up by the before_task_publish signal.
        for key in self.special_headers + self.special_options:
            if kwargs is not None and key in kwargs:
                headers[key] = kwargs.pop(key)
            if key in options:
                headers[key] = options.pop(key)

        if 'headers' in options:
            options['headers'].update(headers)
        else:
            options['headers'] = headers

        return super(Task, self).apply_async(
            args=args, kwargs=kwargs, task_id=task_id, producer=producer,
            link=link, link_error=link_error, shadow=shadow, **options)

    def describe(self):
        # The describe module indirectly depends on this module, so to
        # avoid circular imports, we import describe_function here.
        from describe import describe_function
        return describe_function(self.run)

    def call_item_task(self, inputs, outputs={}):
        return self.run.call_item_task(inputs, outputs)


@before_task_publish.connect
def girder_before_task_publish(sender=None, body=None, exchange=None,
                               routing_key=None, headers=None, properties=None,
                               declare=None, retry_policy=None, **kwargs):
    if 'jobInfoSpec' not in headers:
        try:
            # Note: If we can import these objects from the girder packages we
            # assume our producer is in a girder REST request. This allows
            # us to create the job model's directly. Otherwise there will be an
            # ImportError and we can create the job via a REST request using
            # the jobInfoSpec in headers.
            from girder.utility.model_importer import ModelImporter
            from girder.plugins.worker import utils
            from girder.api.rest import getCurrentUser

            job_model = ModelImporter.model('job', 'jobs')

            user = headers.pop('girder_user', getCurrentUser())
            task_args, task_kwargs = body[0], body[1]

            job = job_model.createJob(
                **{'title': headers.pop('girder_job_title', Task._girder_job_title),
                   'type': headers.pop('girder_job_type', Task._girder_job_type),
                   'handler': headers.pop('girder_job_handler', Task._girder_job_handler),
                   'public': headers.pop('girder_job_public', Task._girder_job_public),
                   'user': user,
                   'args': task_args,
                   'kwargs': task_kwargs,
                   'otherFields': dict(celeryTaskId=headers['id'],
                                       **headers.pop('girder_job_other_fields',
                                                     Task._girder_job_other_fields))})

            headers['jobInfoSpec'] = utils.jobInfoSpec(job)

        except ImportError:
            # TODO: Check for self.job_manager to see if we have
            #       tokens etc to contact girder and create a job model
            #       we may be in a chain or a chord or some-such
            pass

    if 'girder_api_url' not in headers:
        try:
            from girder.plugins.worker import utils
            headers['girder_api_url'] = utils.getWorkerApiUrl()
        except ImportError:
            # TODO: handle situation where girder_worker is producing the message
            #       Note - this may not come up at all depending on how we pass
            #       girder_api_url through to the next task (e.g. in the context
            #       of chaining events)
            pass

    if 'girder_client_token' not in headers:
        try:
            from girder.utility.model_importer import ModelImporter
            headers['girder_client_token'] = ModelImporter.model('token').createToken()
        except ImportError:
            # TODO: handle situation where girder_worker is producing the message
            #       Note - this may not come up at all depending on how we pass
            #       girder_token through to the next task (e.g. in the context
            #       of chaining events)
            pass

    # Finally,  remove all special_options from headers
    for key in Task.special_options:
        headers.pop(key)


@worker_ready.connect
def check_celery_version(*args, **kwargs):
    if LooseVersion(__version__) < LooseVersion('4.0.0'):
        sys.exit("""You are running Celery {}.

girder-worker requires celery>=4.0.0""".format(__version__))


def deserialize_job_info_spec(**kwargs):
    return girder_worker.utils.JobManager(**kwargs)


class JobSpecNotFound(Exception):
    pass


@task_prerun.connect
def gw_task_prerun(task=None, sender=None, task_id=None,
                   args=None, kwargs=None, **rest):
    """Deserialize the jobInfoSpec passed in through the headers.

    This provides the a JobManager class as an attribute of the
    task before task execution.  decorated functions may bind to
    their task and have access to the job_manager for logging and
    updating their status in girder.
    """
    try:
        if hasattr(task.request, 'jobInfoSpec'):
            jobSpec = task.request.jobInfoSpec

        # Deprecated: This method of passing job information
        # to girder_worker is deprecated. Newer versions of girder
        # pass this information automatically as apart of the
        # header metadata in the worker scheduler.
        elif 'jobInfo' in kwargs:
            jobSpec = kwargs.pop('jobInfo', {})

        else:
            raise JobSpecNotFound

        task.job_manager = deserialize_job_info_spec(**jobSpec)

        # For now,  only automatically update status if this is
        # not a child task. Otherwise child tasks completion will
        # update the parent task's jobModel in girder.
        if task.request.parent_id is None:
            task.job_manager.updateStatus(JobStatus.RUNNING)

    except JobSpecNotFound:
        task.job_manager = None
        print('Warning: No jobInfoSpec. Setting job_manager to None.')


@task_success.connect
def gw_task_success(sender=None, **rest):
    try:
        if sender.request.parent_id is None:
            sender.job_manager.updateStatus(JobStatus.SUCCESS)

    except AttributeError:
        pass


@task_failure.connect
def gw_task_failure(sender=None, exception=None,
                    traceback=None, **rest):
    try:

        msg = '%s: %s\n%s' % (
            exception.__class__.__name__, exception,
            ''.join(tb.format_tb(traceback)))

        sender.job_manager.write(msg)

        if sender.request.parent_id is None:
            sender.job_manager.updateStatus(JobStatus.ERROR)

    except AttributeError:
        pass


@task_postrun.connect
def gw_task_postrun(task=None, sender=None, task_id=None,
                    args=None, kwargs=None,
                    retval=None, state=None, **rest):
    try:
        task.job_manager._flush()
        task.job_manager._redirectPipes(False)
    except AttributeError:
        pass


class _CeleryConfig:
    CELERY_ACCEPT_CONTENT = ['json', 'pickle', 'yaml']


broker_uri = girder_worker.config.get('celery', 'broker')
try:
    backend_uri = girder_worker.config.get('celery', 'backend')
except configparser.NoOptionError:
    backend_uri = broker_uri

app = Celery(
    main=girder_worker.config.get('celery', 'app_main'),
    backend=backend_uri, broker=broker_uri,
    task_cls='girder_worker.app:Task')

app.config_from_object(_CeleryConfig)
