#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2015 Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import os
import re
import setuptools
import shutil

from pkg_resources import parse_requirements
from setuptools.command.install import install

# Note to future developers:
# tl;dr - don't copy this function!
#
# This function is a compromise and not a recommended way of approaching this
# problem. Ideally install_requires should statically define the minimum
# versions of immediate dependencies allowing developers to experiment with
# new upstream features. extra_requires should point to separate pip install
# -able packages for plugins like girder_io, docker, r, etc which should be
# managed through entry_points or with an entry point based plugin management
# package like stevedore (https://pypi.python.org/pypi/stevedore). This would
# allow each application plugin (e.g. girder_io) to manage its own dependencies
# separately from girder_worker. But - until such time as an approach like this
# is implemented we directly read requirements.txt files from plugin
# directories and "unpin" them to ensure developers are not constrained by
# pinned versions and generally to avoid dependency hell.
def unpin_version(r):
    """
    Generate an identical package requirement string but replace any pinned
    version (e.g. ==3.2.0)  with unpinned, minimum versions (e.g. >=3.2.0).
    This function takes a pkg_resources Requirement object and returns a string
    """
    try:
        name = r.name
        extras = '[{}]'.format(','.join(r.extras)) if r.extras else ''
        marker = ' ;{}'.format(str(r.marker)) if r.marker else ''

        # version spec OR url,  not both
        if r.url is not None:
            # No meaningful way to 'unpin' a URL version
            version = ' @{}'.format(r.url) if r.url else ''

        else:
            # Convert any '==' requirements to '>=' requirements
            version = ' {}'.format(
                ','.join([">={}".format(version) if op == '==' else op + version
                          for op, version in r.specs]))

        return str(r.parse("{}{}{}{}".format(
            name, extras, version, marker
        )))

    except Exception:
        return str(r)


class CustomInstall(install):
    """
    Override the default install to add some custom install-time behavior.
    Namely, we create the local config file.
    """
    def run(self, *args, **kwargs):
        install.run(self, *args, **kwargs)

        distcfg = os.path.join('girder_worker', 'worker.dist.cfg')
        localcfg = os.path.join('girder_worker', 'worker.local.cfg')
        if not os.path.isfile(localcfg):
            print('Creating worker.local.cfg')
            shutil.copyfile(distcfg, localcfg)


init = os.path.join(os.path.dirname(__file__), 'girder_worker', '__init__.py')
with open(init) as fd:
    version = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
        fd.read(), re.MULTILINE).group(1)

with open('README.rst') as f:
    readme = f.read()

plugin_data = []
# We must manually glob for plugin data since setuptools package_data
# errors out when trying to include directories recursively
os.chdir('girder_worker')
for root, dirnames, filenames in os.walk('plugins'):
    plugin_data.extend([os.path.join(root, fn) for fn in filenames])
os.chdir('..')

# parse_requirements() returns generator of pip.req.InstallRequirement objects
install_reqs = []
try:
    with open('requirements.txt') as f:
        install_reqs = parse_requirements(f.read())
except Exception:
    pass
reqs = [unpin_version(req) for req in install_reqs]

# Build up extras_require for plugin requirements
extras_require = {}
plugins_dir = os.path.join('girder_worker', 'plugins')
for name in os.listdir(plugins_dir):
    reqs_file = os.path.join(plugins_dir, name, 'requirements.txt')
    if os.path.isfile(reqs_file):
        with open(reqs_file) as f:
            plugin_reqs = parse_requirements(f.read())
        extras_require[name] = [unpin_version(r) for r in plugin_reqs]
    else:
        extras_require[name] = []

# perform the install
setuptools.setup(
    name='girder-worker',
    version=version,
    description='Batch execution engine built on celery.',
    long_description=readme,
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    url='https://github.com/girder/girder_worker',
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2'
    ],
    extras_require=extras_require,
    packages=setuptools.find_packages(
        exclude=('tests.*', 'tests')
    ),
    package_data={
        'girder_worker': [
            'worker.dist.cfg',
            'worker.local.cfg',
            'format/**/*'
        ] + plugin_data
    },
    cmdclass={
        'install': CustomInstall
    },
    install_requires=reqs,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'girder-worker = girder_worker.__main__:main',
            'girder-worker-config = girder_worker.configure:main'
        ],
        'girder_worker_plugins': [
            'core = girder_worker:GirderWorkerPlugin'
        ]
    }
)
