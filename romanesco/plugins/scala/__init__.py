import romanesco
from . import executor


def load(params):
    romanesco.register_executor('scala', executor.run)
    romanesco.register_executor('spark.scala', executor.run_spark)
