import girder_worker
from . import executor


def load(params):
    girder_worker.register_executor('scala', executor.run)
    girder_worker.register_executor('spark.scala', executor.run_spark)
