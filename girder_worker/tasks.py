import core
from .core.utils import JobManager, JobStatus
from .app import app


@app.task(name='girder_worker.run')
def run(*pargs, **kwargs):
    jobInfo = kwargs.pop('jobInfo', {})

    with JobManager(logPrint=jobInfo.get('logPrint', True),
                    url=jobInfo.get('url'), method=jobInfo.get('method'),
                    headers=jobInfo.get('headers'),
                    reference=jobInfo.get('reference')) as jm:
        kwargs['_job_manager'] = jm
        kwargs['status'] = JobStatus.RUNNING
        return core.run(*pargs, **kwargs)
