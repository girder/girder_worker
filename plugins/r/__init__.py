import os
import romanesco
from . import executor

def load(params):
    romanesco.register_executor('r', executor.run)

    converters_dir = os.path.join(params['plugin_dir'], 'converters')
    romanesco.format.import_converters([
        os.path.join(converters_dir, 'r'),
        os.path.join(converters_dir, 'table'),
        os.path.join(converters_dir, 'tree')
    ])
