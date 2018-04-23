import abc
import os
from pkg_resources import DistributionNotFound, get_distribution
from six.moves.configparser import SafeConfigParser

from . import log_utils


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


__license__ = 'Apache 2.0'

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
# Read the configuration files
_cfgs = ('worker.dist.cfg', 'worker.local.cfg')


config = SafeConfigParser({
    'RABBITMQ_USER': os.environ.get('RABBITMQ_USER', 'guest'),
    'RABBITMQ_PASS': os.environ.get('RABBITMQ_PASS', 'guest'),
    'RABBITMQ_HOST': os.environ.get('RABBITMQ_HOST', 'localhost')
})

config.read([os.path.join(PACKAGE_DIR, f) for f in _cfgs])

# Create and configure our logger
logger = log_utils.setupLogger(config)


class GirderWorkerPluginABC(object):
    """ """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __init__(self, app, *args, **kwargs):
        """ """
    @abc.abstractmethod
    def task_imports(self):
        """ """


class GirderWorkerPlugin(GirderWorkerPluginABC):

    def __init__(self, app, *args, **kwargs):
        self.app = app

    def task_imports(self):
        return ['girder_worker.tasks']
