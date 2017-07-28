import time

from girder_worker.utils import girder_job
from girder_worker.app import app


@girder_job(title='Cancelable Job')
@app.task(bind=True)
def cancelable(task, **kwargs):
    count = 0
    while not task.canceled and count < 10:
        time.sleep(0.5)
        count += 1


@girder_job(title='Sleeper Job')
@app.task(bind=True)
def sleep(task, **kwargs):
    time.sleep(0.5)
