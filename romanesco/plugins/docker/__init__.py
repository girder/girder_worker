import romanesco
from . import executor


def load(params):
    romanesco.register_executor('docker', executor.run)
