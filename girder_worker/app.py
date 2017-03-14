import girder_worker
import traceback as tb
from celery import Celery, __version__
from distutils.version import LooseVersion
from celery.signals import (task_prerun, task_postrun,
                            task_failure, task_success, worker_ready)
from .utils import JobStatus


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
    broker=girder_worker.config.get('celery', 'broker'))

app.config_from_object(_CeleryConfig)
