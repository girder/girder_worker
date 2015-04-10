import romanesco

from .utils import JobManager
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
                        headers=jobInfo.get('headers')):
            retval = romanesco.run(*pargs, **kwargs)
        return retval

    @app.task
    def convert(*pargs, **kwargs):
        return romanesco.convert(*pargs, **kwargs)

    app.worker_main()


if __name__ == '__main__':
    main()
