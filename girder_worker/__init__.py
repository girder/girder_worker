import abc
import os
from ConfigParser import SafeConfigParser

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
# Read the configuration files
_cfgs = ('worker.dist.cfg', 'worker.local.cfg')
config = SafeConfigParser(os.environ)
config.read([os.path.join(PACKAGE_DIR, f) for f in _cfgs])



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
