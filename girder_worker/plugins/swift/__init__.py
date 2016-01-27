import girder_worker
from . import executor


def load(params):
    girder_worker.register_executor('swift', executor.run)
