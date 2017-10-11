from __future__ import print_function
from ConfigParser import ConfigParser

import argparse
import os
import pip
import sys


def main(args):
    basePath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Read the configuration files
    files = ('worker.dist.cfg', 'worker.local.cfg')
    config = ConfigParser()
    config.read([os.path.join(basePath, 'girder_worker', f) for f in files])
    os.chdir(basePath)
    plugins = os.environ.get(
        'GIRDER_WORKER_PLUGINS_ENABLED',
        config.get('girder_worker', 'plugins_enabled'))
    plugins = [p.strip() for p in plugins.split(',') if p.strip()]

    installArgs = ['requirements.in']
    if args.mode in ('dev', 'devel', 'development'):
        installArgs.append('requirements-dev.in')

    # Install plugins requirements files
    pluginsDir = os.path.join('girder_worker', 'plugins')
    for path in os.listdir(pluginsDir):
        if args.all or path in plugins:
            pluginReqs = os.path.join(pluginsDir, path, 'requirements.txt')
            if os.path.exists(os.path.join(basePath, pluginReqs)):
                installArgs.append(pluginReqs)

    pipArgs = ['install'] + [
        os.path.join('-r' + basePath, req) for req in installArgs
    ]

    print('\033[32m*** Installing: %s\033[0m' % ' '.join(installArgs))
    if pip.main(pipArgs) != 0:
        print('\033[1;91m*** Error installing %s, stopping.\033[0m' % file,
              file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Install required pip packages.')
    parser.add_argument('-m', '--mode', default='prod',
                        help='install for "dev" or "prod" (the default)')
    parser.add_argument('-a', '--all', help='install requirements of all '
                        'plugins rather than just enabled ones',
                        action='store_true')
    args = parser.parse_args()

    main(args)
