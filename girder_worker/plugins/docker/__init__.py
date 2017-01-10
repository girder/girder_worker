def before_run(e):
    import executor
    if e.info['task']['mode'] == 'docker':
        executor.validate_task_outputs(e.info['task_outputs'])


def load(params):
    from girder_worker.core import events, register_executor
    import executor

    events.bind('run.before', 'docker', before_run)
    register_executor('docker', executor.run)
