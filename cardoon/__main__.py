import cardoon
from celery import Celery

if __name__ == "__main__":
    app = Celery(
        main='cardoon',
        backend='mongodb://localhost/cardoon',
        broker='mongodb://localhost/cardoon')

    @app.task
    def run(*pargs, **kwargs):
        return cardoon.run(*pargs, **kwargs)

    app.worker_main()
