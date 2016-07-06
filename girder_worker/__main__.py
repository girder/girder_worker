import girder_worker
from girder_worker.format import conv_graph

from .utils import JobManager, JobStatus
from celery import Celery

app = None


class _CeleryConfig:
    CELERY_ACCEPT_CONTENT = ['json', 'pickle', 'yaml']


def main():
    global app
    app = Celery(
        main=girder_worker.config.get('celery', 'app_main'),
        backend=girder_worker.config.get('celery', 'broker'),
        broker=girder_worker.config.get('celery', 'broker'))
    app.config_from_object(_CeleryConfig)

    @app.task
    def run(*pargs, **kwargs):
        jobInfo = kwargs.pop('jobInfo', {})
        retval = 0

        with JobManager(logPrint=jobInfo.get('logPrint', True),
                        url=jobInfo.get('url'), method=jobInfo.get('method'),
                        headers=jobInfo.get('headers'),
                        reference=jobInfo.get('reference')) as jm:
            kwargs['_job_manager'] = jm
            kwargs['status'] = JobStatus.RUNNING
            retval = girder_worker.run(*pargs, **kwargs)
        return retval

    @app.task
    def convert(*pargs, **kwargs):
        return girder_worker.convert(*pargs, **kwargs)

    @app.task
    def validators(*pargs, **kwargs):
        _type, _format = pargs
        nodes = []

        for (node, data) in conv_graph.nodes(data=True):
            if ((_type is None) or (_type == node.type)) and \
               ((_format is None) or (_format == node.format)):
                nodes.append({'type': node.type,
                              'format': node.format,
                              'validator': data})

        return nodes

    app.worker_main()


if __name__ == '__main__':
    main()
