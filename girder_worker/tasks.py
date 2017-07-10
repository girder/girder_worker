import core
from girder_worker.utils import JobStatus
from .app import app


def _cleanup(*args, **kwargs):
    core.events.trigger('cleanup')


@app.task(name='girder_worker.run', bind=True, after_return=_cleanup)
def run(_celery_task, *pargs, **kwargs):
    kwargs['_job_manager'] = _celery_task.job_manager \
        if hasattr(_celery_task, 'job_manager') else None

    kwargs['_celery_task'] = _celery_task

    kwargs['status'] = JobStatus.RUNNING

    return core.run(*pargs, **kwargs)
