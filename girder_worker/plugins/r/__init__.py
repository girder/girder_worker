import os


def load(params):
    from girder_worker.core import register_executor
    from girder_worker.plugins.types import format
    from . import executor

    register_executor('r', executor.run)

    converters_dir = os.path.join(params['plugin_dir'], 'converters')
    format.import_converters([
        os.path.join(converters_dir, 'r'),
        os.path.join(converters_dir, 'table'),
        os.path.join(converters_dir, 'tree')
    ])
