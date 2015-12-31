import romanesco
from romanesco.format import conv_graph

from .utils import JobManager, JobStatus
from celery import Celery

app = None


def main():
    global app
    app = Celery(
        main=romanesco.config.get('celery', 'app_main'),
        backend=romanesco.config.get('celery', 'broker'),
        broker=romanesco.config.get('celery', 'broker'))

    @app.task
    def run(*pargs, **kwargs):
        jobInfo = kwargs.pop('jobInfo', {})
        retval = 0

        with JobManager(logPrint=jobInfo.get('logPrint', True),
                        url=jobInfo.get('url'), method=jobInfo.get('method'),
                        headers=jobInfo.get('headers')) as jm:
            kwargs['_job_manager'] = jm
            kwargs['status'] = JobStatus.RUNNING
            retval = romanesco.run(*pargs, **kwargs)
        return retval

    @app.task
    def convert(*pargs, **kwargs):
        return romanesco.convert(*pargs, **kwargs)

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
