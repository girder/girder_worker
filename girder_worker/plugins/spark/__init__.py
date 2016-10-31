import os

SC_KEY = '_girder_worker_spark_context'


def setup_pyspark_task(event):
    """
    This is executed before a task execution. If it is a pyspark task, we
    create the spark context here so it can be used for any input conversion.
    """
    from . import spark
    info = event.info
    if info['mode'] == 'spark.python' and SC_KEY not in info['kwargs']:
        spark_conf = info['task'].get('spark_conf', {})
        info['kwargs'][SC_KEY] = spark.create_spark_context(spark_conf)
        info['cleanup_spark'] = True


def pyspark_run_cleanup(event):
    if event.info.get('cleanup_spark'):
        event.info['kwargs'][SC_KEY].stop()


def load(params):
    import girder_worker
    from girder_worker.core import events, format, register_executor
    from . import pyspark_executor, spark

    # If we have a spark config section then try to setup spark environment
    if girder_worker.config.has_section('spark') or 'SPARK_HOME' in os.environ:
        spark.setup_spark_env()

    register_executor('spark.python', pyspark_executor.run)

    events.bind('run.before', 'spark', setup_pyspark_task)
    events.bind('run.finally', 'spark', pyspark_run_cleanup)

    format.import_converters(
        os.path.join(params['plugin_dir'], 'converters'))
