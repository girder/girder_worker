import girder_worker
import girder_worker.events
from . import executor


def load(params):
    girder_worker.events.bind(
        'run.before', 'docker',
        lambda e: executor.validate_task_outputs(e.info['task_outputs']))

    girder_worker.register_executor('docker', executor.run)
