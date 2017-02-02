import abc
import logging
import os
from ConfigParser import SafeConfigParser

__version__ = '0.3.0'
__license__ = 'Apache 2.0'

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
# Read the configuration files
_cfgs = ('worker.dist.cfg', 'worker.local.cfg')
config = SafeConfigParser(os.environ)
config.read([os.path.join(PACKAGE_DIR, f) for f in _cfgs])

# The root logger is used as a placeholder for the moment, but this
# should be configurable via config files later. TODO
logger = logging


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
