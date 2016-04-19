import girder_worker
import girder_worker.events
from . import executor


def before_run(e):
    if e.info['task']['mode'] == 'docker':
        executor.validate_task_outputs(e.info['task_outputs'])


def load(params):
    girder_worker.events.bind('run.before', 'docker', before_run)
    girder_worker.register_executor('docker', executor.run)
