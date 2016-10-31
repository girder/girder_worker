import os
from girder_worker.core import register_executor, format
from . import executor


def load(params):
    register_executor('r', executor.run)

    converters_dir = os.path.join(params['plugin_dir'], 'converters')
    format.import_converters([
        os.path.join(converters_dir, 'r'),
        os.path.join(converters_dir, 'table'),
        os.path.join(converters_dir, 'tree')
    ])
