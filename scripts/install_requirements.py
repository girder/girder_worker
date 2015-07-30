from __future__ import print_function
from ConfigParser import ConfigParser

import argparse
import os
import subprocess
import sys


def installReqs(file, pip):
    if not os.path.exists(file):
        return

    print('\033[32m*** Installing: %s\033[0m' % file)
    if subprocess.call([pip, 'install', '-U', '-r', file]) != 0:
        print('\033[1;91m*** Error installing %s, stopping.\033[0m' % file,
              file=sys.stderr)
        sys.exit(1)


def installFromDir(path, dev, pip):
    installReqs(os.path.join(path, 'requirements.txt'), pip)

    if dev:
        installReqs(os.path.join(path, 'requirements-dev.txt'), pip)


def main(args):
    basePath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Read the configuration files
    files = ('worker.dist.cfg', 'worker.local.cfg')
    config = ConfigParser()
    config.read([os.path.join(basePath, 'romanesco', f) for f in files])
    os.chdir(basePath)
    isDevMode = args.mode in ('dev', 'devel', 'development')
    plugins = os.environ.get('ROMANESCO_PLUGINS_ENABLED',
                              config.get('romanesco', 'plugins_enabled'))
    plugins = [p.strip() for p in plugins.split(',') if p.strip()]

    # Install core requirements files
    installFromDir(basePath, isDevMode, args.pip)

    # Install plugins requirements files
    pluginsDir = os.path.join(basePath, 'plugins')
    for path in os.listdir(pluginsDir):
        if args.all or path in plugins:
            pluginPath = os.path.join(pluginsDir, path)
            if os.path.isdir(pluginPath):
                installFromDir(pluginPath, isDevMode, args.pip)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Install required pip packages.')
    parser.add_argument('-m', '--mode', default='prod',
                        help='install for "dev" or "prod" (the default)')
    parser.add_argument('-p', '--pip', default='pip',
                        help='alternate path to pip executable')
    parser.add_argument('-a', '--all', help='install requirements of all '
                        'plugins rather than just enabled ones',
                        action='store_true')
    args = parser.parse_args()

    main(args)
