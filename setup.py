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

from pkg_resources import parse_requirements


with open('README.rst') as f:
    readme = f.read()

with open('plugin.json') as f:
    version = json.load(f)['version']

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
            'format/**/*',
            'plugins/**/*'
        ]
    },
    install_requires=reqs,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'romanesco-worker = romanesco.__main__:main'
        ]
    }
)
