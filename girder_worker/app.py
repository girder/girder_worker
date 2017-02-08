import girder_worker
from celery import Celery
from celery.signals import task_prerun


def deserialize_job_info_spec(**kwargs):
    return girder_worker.utils.JobManager(**kwargs)

@task_prerun.connect
def gw_task_prerun(task=None, sender=None, task_id=None,
                   task_args=None, task_kwargs=None, **kwargs):
    """Deserialize the jobInfoSpec passed in through the headers.

    This provides the a JobManager class as an attribute of the
    task before task execution.  decorated functions may bind to
    thier task and have access to the job_manager for logging and
    updating their status in girder.
    """
    try:
        task.job_manager = deserialize_job_info_spec(
            **task.request.headers['jobInfoSpec'])
    except KeyError:
        task.job_manager = None
        # Log warning here?


class _CeleryConfig:
    CELERY_ACCEPT_CONTENT = ['json', 'pickle', 'yaml']

app = Celery(
    main=girder_worker.config.get('celery', 'app_main'),
    backend=girder_worker.config.get('celery', 'broker'),
    broker=girder_worker.config.get('celery', 'broker'))

app.config_from_object(_CeleryConfig)
