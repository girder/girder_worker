import romanesco
from celery import Celery

if __name__ == "__main__":
    app = Celery(
        main='romanesco',
        backend='mongodb://localhost/romanesco',
        broker='mongodb://localhost/romanesco')

    @app.task
    def run(*pargs, **kwargs):
        return romanesco.run(*pargs, **kwargs)

    @app.task
    def convert(*pargs, **kwargs):
        return romanesco.convert(*pargs, **kwargs)

    app.worker_main()
