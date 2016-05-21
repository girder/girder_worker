import girder_worker
import girder_worker.events
import platform
from . import executor


def before_run(e):
    if e.info['task']['mode'] == 'docker':
        executor.validate_task_outputs(e.info['task_outputs'])


def load(params):
    if platform.system() != 'Linux':
        raise Exception('The docker plugin only works on Linux hosts due to
                        'mapping of shared volumes and pipes between host and '
                        'container.')
    girder_worker.events.bind('run.before', 'docker', before_run)
    girder_worker.register_executor('docker', executor.run)
