def load(params):
    from girder_worker.core import register_executor
    from . import executor

    register_executor('swift', executor.run)
