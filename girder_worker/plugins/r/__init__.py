import os
import girder_worker
from . import executor


def load(params):
    girder_worker.register_executor('r', executor.run)

    converters_dir = os.path.join(params['plugin_dir'], 'converters')
    girder_worker.format.import_converters([
        os.path.join(converters_dir, 'r'),
        os.path.join(converters_dir, 'table'),
        os.path.join(converters_dir, 'tree')
    ])
