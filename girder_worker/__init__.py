import os
from ConfigParser import SafeConfigParser

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
# Read the configuration files
_cfgs = ('worker.dist.cfg', 'worker.local.cfg')
config = SafeConfigParser(os.environ)
config.read([os.path.join(PACKAGE_DIR, f) for f in _cfgs])
