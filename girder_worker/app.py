import girder_worker
import traceback as tb
import celery
from celery import Celery, __version__
from distutils.version import LooseVersion
from celery.signals import (task_prerun, task_postrun,
                            task_failure, task_success,
                            worker_ready, before_task_publish)
from celery.result import AsyncResult
from celery.task.control import inspect

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

    _girder_job_title = None
    _girder_job_type = None
    _girder_job_public = False
    _girder_job_handler = 'celery_handler'
    _girder_job_other_fields = {}

    special_headers = ['girder_token', 'girder_user']

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
        for key in self.special_headers:
            if kwargs is not None and key in kwargs:
                headers[key] = kwargs.pop(key)
            if key in options:
                headers[key] = options.pop(key)

        headers['girder_job_title'] = self._girder_job_title
        headers['girder_job_type'] = self._girder_job_type
        headers['girder_job_public'] = self._girder_job_public
        headers['girder_job_handler'] = self._girder_job_handler
        headers['girder_job_other_fields'] = self._girder_job_other_fields

        if 'headers' in options:
            options['headers'].update(headers)
        else:
            options['headers'] = headers

        return super(Task, self).apply_async(
            args=args, kwargs=kwargs, task_id=task_id, producer=producer,
            link=link, link_error=link_error, shadow=shadow, **options)


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
            token = headers.pop('girder_token', None)

            task_args, task_kwargs = body[0], body[1]

            job = job_model.createJob(
                **{'title': headers.get('girder_job_title', Task._girder_job_title),
                   'type': headers.get('girder_job_type', Task._girder_job_type),
                   'handler': headers.get('girder_job_handler', Task._girder_job_handler),
                   'public': headers.get('girder_job_public', Task._girder_job_public),
                   'user': user,
                   'args': task_args,
                   'kwargs': task_kwargs,
                   'otherFields': dict(celeryTaskId=headers['id'],
                                       **headers.get('girder_job_other_fields',
                                                     Task._girder_job_other_fields))})
            # If we don't have a token from girder_token kwarg,  use
            # the job token instead. Otherwise no token
            if token is None:
                token = job.get('token', None)

            headers['jobInfoSpec'] = utils.jobInfoSpec(job, token)
            headers['apiUrl'] = utils.getWorkerApiUrl()

        except ImportError:
            # TODO: Check for self.job_manager to see if we have
            #       tokens etc to contact girder and create a job model
            #       we may be in a chain or a chord or some-such
            pass


@worker_ready.connect
def check_celery_version(*args, **kwargs):
    if LooseVersion(__version__) < LooseVersion('4.0.0'):
        print("""You are running Celery {}.

Celery 3.X is being deprecated in girder-worker!

Common APIs are compatible so we do not expect significant disruption.
Please verify that your system works with Celery 4.X as soon as possible."""
              .format(__version__))


def deserialize_job_info_spec(**kwargs):
    return girder_worker.utils.JobManager(**kwargs)


class JobSpecNotFound(Exception):
    pass


# ::: NOTE :::
# This is a transitional function for managing compatability between
# Celery 3.X and 4.X. The issue is how child tasks,  spawned from
# girder-worker, handle their status updates and logging. In Celery 3.X
# there is no easy way to determine if a task was spawned by another
# task and so all status updates/logs are sent to the same girder job
# model.  In Celery 4.X task ancestry is handled through the parent_id
# attribute. So for Celery 4.X child tasks will report nothing,  for
# Celery 3.X child tasks report everything to the same girder JobModel.
# This is not an ideal situation, and while the path forward is to
# transition to Celery 4, this function exists to temporarily provide
# backwards compatability with Celery 3.X while projects transition.
def _update_status(task, status):
    # Celery 4.X
    if hasattr(task.request, 'parent_id'):
        # For now,  only automatically update status if this is
        # not a child task. Otherwise child tasks completion will
        # update the parent task's jobModel in girder.
        if task.request.parent_id is None:
            task.job_manager.updateStatus(status)
    # Celery 3.X
    else:
        task.job_manager.updateStatus(status)


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
        # Celery 4.x API
        if hasattr(task.request, 'jobInfoSpec'):
            jobSpec = task.request.jobInfoSpec

        # Celery 3.X API
        elif task.request.headers is not None and \
                'jobInfoSpec' in task.request.headers:
            jobSpec = task.request.headers['jobInfoSpec']

        # Deprecated: This method of passing job information
        # to girder_worker is deprecated. Newer versions of girder
        # pass this information automatically as apart of the
        # header metadata in the worker scheduler.
        elif 'jobInfo' in kwargs:
            jobSpec = kwargs.pop('jobInfo', {})

        else:
            raise JobSpecNotFound

        task.job_manager = deserialize_job_info_spec(**jobSpec)

        _update_status(task, JobStatus.RUNNING)

    except JobSpecNotFound:
        task.job_manager = None
        print('Warning: No jobInfoSpec. Setting job_manager to None.')


@task_success.connect
def gw_task_success(sender=None, **rest):
    try:
        status = JobStatus.SUCCESS
        if is_revoked(sender):
            status = JobStatus.CANCELED
        _update_status(sender, status)
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

        _update_status(sender, JobStatus.ERROR)
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


# Access to the correct "Inspect" instance for this worker
_inspector = None


def _worker_inspector(task):
    global _inspector
    if _inspector is None:
        _inspector = inspect([task.request.hostname])

    return _inspector


# Get this list of currently revoked tasks for this worker
def _revoked_tasks(task):
    return _worker_inspector(task).revoked()[task.request.hostname]


def is_revoked(task):
    """
    Utility function to check is a task has been revoked.

    :param task: The task.
    :type task: celery.app.task.Task
    :return True, if this task is in the revoked list for this worker, False
            otherwise.
    """
    return task.request.id in _revoked_tasks(task)


class _CeleryConfig:
    CELERY_ACCEPT_CONTENT = ['json', 'pickle', 'yaml']


app = Celery(
    main=girder_worker.config.get('celery', 'app_main'),
    backend=girder_worker.config.get('celery', 'broker'),
    broker=girder_worker.config.get('celery', 'broker'),
    task_cls='girder_worker.app:Task')

app.config_from_object(_CeleryConfig)
