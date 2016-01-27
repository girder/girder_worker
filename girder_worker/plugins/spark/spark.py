import girder_worker
import os
import sys

from ConfigParser import NoOptionError, NoSectionError


def setup_spark_env():
    # Setup pyspark
    spark_home = None

    try:
        spark_home = girder_worker.config.get('spark', 'spark_home')
    except (NoOptionError, NoSectionError):
        pass

    # If not configured try the environment
    if not spark_home:
        spark_home = os.environ.get('SPARK_HOME')

    if not spark_home:
        raise Exception('spark_home must be set or SPARK_HOME must be set in '
                        'the environment')

    # Need to set SPARK_HOME
    os.environ['SPARK_HOME'] = spark_home

    if not os.path.exists(spark_home):
        raise Exception('spark_home is not a valid directory')

    sys.path.append(os.path.join(spark_home, 'python'))
    sys.path.append(os.path.join(spark_home, 'bin'))

    # Check that we can import SparkContext
    from pyspark import SparkConf, SparkContext  # noqa


def create_spark_context(task_spark_conf):
    from pyspark import SparkConf, SparkContext
    # Set can spark configuration parameter user has specified
    spark_conf = SparkConf()

    if girder_worker.config.has_section('spark'):
        for (name, value) in girder_worker.config.items('spark'):
            spark_conf.set(name, value)

    # Override with any task specific configuration
    for (name, value) in task_spark_conf.items():
        spark_conf.set(name, value)

    # Build up the context, using the master URL
    sc = SparkContext(conf=spark_conf)

    return sc
