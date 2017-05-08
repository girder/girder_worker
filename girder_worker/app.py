import girder_worker
import traceback as tb
import celery
from celery import Celery, __version__
from distutils.version import LooseVersion
from celery.signals import (task_prerun, task_postrun,
                            task_failure, task_success, worker_ready)
from .utils import JobStatus


class Task(celery.Task):
    """Girder Worker Task object"""

    _girder_job_title = None
    _girder_job_type = None
    _girder_job_public = False
    _girder_job_handler = 'celery_handler'
    _girder_job_other_fields = {}

    def job_description(self, user=None, args=(), kwargs=()):
        # Note that celery_handler should not be bound
        # to any schedule event in girder. This prevents
        # the job from being accidentally scheduled and being
        # passed to the 'worker_handler' code
        return {
            'title': self._girder_job_title,
            'type': self._girder_job_type,
            'handler': self._girder_job_handler,
            'public': self._girder_job_public,
            'user': user,
            'args': args,
            'kwargs': kwargs,
            'otherFields': self._girder_job_other_fields
        }

    def apply_async(self, args=None, kwargs=None, task_id=None, producer=None,
                    link=None, link_error=None, shadow=None, **options):
        try:
            # If we can import these we assume our producer is girder
            # We can create the job model's directly
            from girder.utility.model_importer import ModelImporter
            from girder.plugins.worker import utils
            from girder.api.rest import getCurrentUser

            job_model = ModelImporter.model('job', 'jobs')

            user = options.pop('girder_user', getCurrentUser())
            token = options.pop('girder_token', None)

            job = job_model.createJob(**self.job_description(user, args, kwargs))

            # If we don't have a token from girder_token kwarg,  use
            # the job token instead. Otherwise no token
            if token is None:
                token = job.get('token', None)

            headers = {
                'jobInfoSpec': utils.jobInfoSpec(job, token),
                'apiUrl': utils.getWorkerApiUrl()
            }

            if 'headers' in options:
                options['headers'].update(headers)
            else:
                options['headers'] = headers

            async_result = super(Task, self).apply_async(
                args=args, kwargs=kwargs, task_id=task_id, producer=producer,
                link=link, link_error=link_error, shadow=shadow, **options)

            async_result.job = job
            return async_result

        except ImportError:
            # TODO: Check for self.job_manager to see if we have
            #       tokens etc to contact girder and create a job model
            #       we may be in a chain or a chord or some-such
            async_result = super(Task, self).apply_async(
                args=args, kwargs=kwargs, task_id=task_id, producer=producer,
                link=link, link_error=link_error, shadow=shadow, **options)

            async_result.job = None
            return async_result


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
        _update_status(sender, JobStatus.SUCCESS)
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


class _CeleryConfig:
    CELERY_ACCEPT_CONTENT = ['json', 'pickle', 'yaml']


app = Celery(
    main=girder_worker.config.get('celery', 'app_main'),
    backend=girder_worker.config.get('celery', 'broker'),
    broker=girder_worker.config.get('celery', 'broker'),
    task_cls='girder_worker.app:Task')

app.config_from_object(_CeleryConfig)
