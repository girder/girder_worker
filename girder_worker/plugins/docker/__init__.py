import os
import platform


def before_run(e):
    import executor
    if e.info['task']['mode'] == 'docker':
        executor.validate_task_outputs(e.info['task_outputs'])


def load(params):
    from girder_worker.core import events, register_executor
    import executor

    if (platform.system() != 'Linux' and
            not os.environ.get('WORKER_FORCE_DOCKER_START')):
        raise Exception('The docker plugin only works on Linux hosts due to '
                        'mapping of shared volumes and pipes between host and '
                        'container.')
    events.bind('run.before', 'docker', before_run)
    register_executor('docker', executor.run)
