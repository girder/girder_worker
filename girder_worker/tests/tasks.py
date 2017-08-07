from girder_worker.app import app
from girder_worker.describe import argument, types


def not_a_task():
    pass


@argument('n', types.Integer)
def function_task(n):
    return n


@app.task
@argument('n', types.Integer)
def celery_task(n):
    return n
