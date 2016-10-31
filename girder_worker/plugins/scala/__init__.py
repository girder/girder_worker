def load(params):
    from girder_worker.core import register_executor
    from . import executor

    register_executor('scala', executor.run)
    register_executor('spark.scala', executor.run_spark)
