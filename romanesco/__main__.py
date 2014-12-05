import romanesco
from celery import Celery
from .logger import StdoutLogger

if __name__ == "__main__":
    app = Celery(
        main='romanesco',
        backend='mongodb://localhost/romanesco',
        broker='mongodb://localhost/romanesco')

    @app.task
    def run(*pargs, **kwargs):
        url = kwargs.pop('url')
        headers = kwargs.pop('headers')
        retval = 0
        with StdoutLogger(url, 'PUT', headers):
            retval = romanesco.run(*pargs, **kwargs)
        return retval

    @app.task
    def convert(*pargs, **kwargs):
        return romanesco.convert(*pargs, **kwargs)

    app.worker_main()
