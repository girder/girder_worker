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

import json
import os
import setuptools
import shutil

from pkg_resources import parse_requirements
from setuptools.command.install import install


class CustomInstall(install):
    """
    Override the default install to add some custom install-time behavior.
    Namely, we create the local config file.
    """
    def run(self, *args, **kwargs):
        install.run(self, *args, **kwargs)

        distcfg = os.path.join('romanesco', 'worker.dist.cfg')
        localcfg = os.path.join('romanesco', 'worker.local.cfg')
        if not os.path.isfile(localcfg):
            print('Creating worker.local.cfg')
            shutil.copyfile(distcfg, localcfg)


with open('README.rst') as f:
    readme = f.read()

with open('plugin.json') as f:
    version = json.load(f)['version']

plugin_data = []
# We must manually glob for plugin data since setuptools package_data
# errors out when trying to include directories recursively
os.chdir('romanesco')
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
reqs = [str(req) for req in install_reqs]

# Build up extras_require for plugin requirements
extras_require = {}
plugins_dir = os.path.join('romanesco', 'plugins')
for name in os.listdir(plugins_dir):
    reqs_file = os.path.join(plugins_dir, name, 'requirements.txt')
    if os.path.isfile(reqs_file):
        with open(reqs_file) as f:
            plugin_reqs = parse_requirements(f.read())
        extras_require[name] = [str(r) for r in plugin_reqs]
    else:
        extras_require[name] = []

# perform the install
setuptools.setup(
    name='romanesco',
    version=version,
    description='Batch execution engine built on celery.',
    long_description=readme,
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    url='http://romanesco.readthedocs.org',
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
        exclude=('tests.*', 'tests', 'server.*', 'server')
    ),
    package_data={
        'romanesco': [
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
            'romanesco-worker = romanesco.__main__:main'
        ]
    }
)
