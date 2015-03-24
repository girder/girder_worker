import romanesco

from celery import Celery
from ConfigParser import ConfigParser
from .utils import JobManager


_cfgs = ('worker.dist.cfg', 'worker.local.cfg')
config = ConfigParser()
config.read([os.path.join(os.path.dirname(__file__), f) for f in _cfgs])

if __name__ == '__main__':
    app = Celery(
        main=config.get('celery', 'app_main'),
        backend=config.get('celery', 'broker'),
        broker=config.get('celery', 'broker'))

    @app.task
    def run(*pargs, **kwargs):
        jobInfo = kwargs.pop('jobInfo')
        retval = 0
        with JobManager(logPrint=jobInfo.get('logPrint', True),
                        url=jobInfo['url'], headers=jobInfo.get('headers')):
            retval = romanesco.run(*pargs, **kwargs)
        return retval

    @app.task
    def convert(*pargs, **kwargs):
        return romanesco.convert(*pargs, **kwargs)

    app.worker_main()
