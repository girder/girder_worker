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
import shutil
import setuptools


from setuptools.command.install import install


def prerelease_local_scheme(version):
    """Return local scheme version unless building on master in CircleCI.

    This function returns the local scheme version number
    (e.g. 0.0.0.dev<N>+g<HASH>) unless building on CircleCI for a
    pre-release in which case it ignores the hash and produces a
    PEP440 compliant pre-release version number (e.g. 0.0.0.dev<N>).

    """

    from setuptools_scm.version import get_local_node_and_date

    if 'CIRCLE_BRANCH' in os.environ and \
       os.environ['CIRCLE_BRANCH'] == 'master':
        return ''
    else:
        return get_local_node_and_date(version)


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

with open('README.rst') as f:
    readme = f.read()

plugin_data = []
# We must manually glob for plugin data since setuptools package_data
# errors out when trying to include directories recursively
os.chdir('girder_worker')
for root, dirnames, filenames in os.walk('plugins'):
    plugin_data.extend([os.path.join(root, fn) for fn in filenames])
os.chdir('..')

with open('requirements.in') as f:
    install_reqs = f.readlines()

# Build up extras_require for plugin requirements
extras_require = {}
plugins_dir = os.path.join('girder_worker', 'plugins')
for name in os.listdir(plugins_dir):
    reqs_file = os.path.join(plugins_dir, name, 'requirements.txt')
    if os.path.isfile(reqs_file):
        with open(reqs_file) as f:
            extras_require[name] = f.readlines()

# perform the install
setuptools.setup(
    name='girder-worker',
    use_scm_version={'local_scheme': prerelease_local_scheme},
    setup_requires=['setuptools_scm'],
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
            'core/format/**/*'
        ] + plugin_data
    },
    cmdclass={
        'install': CustomInstall
    },
    install_requires=install_reqs,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'girder-worker = girder_worker.__main__:main',
            'girder-worker-cleanup = girder_worker.core.cleanup:main',
            'girder-worker-config = girder_worker.configure:main'
        ],
        'girder_worker_plugins': [
            'core = girder_worker:GirderWorkerPlugin',
            'docker = girder_worker.docker:DockerPlugin [docker]'
        ],
        'girder_worker._test_plugins.valid_plugins': [
            'core = girder_worker._test_plugins.plugins:TestCore',
            'plugin1 = girder_worker._test_plugins.plugins:TestPlugin1',
            'plugin2 = girder_worker._test_plugins.plugins:TestPlugin2'
        ],
        'girder_worker._test_plugins.invalid_plugins': [
            'core = girder_worker._test_plugins.plugins:TestCore',
            'exception1 = girder_worker._test_plugins.plugins:TestPluginException1', # noqa
            'exception2 = girder_worker._test_plugins.plugins:TestPluginException2', # noqa
            'import = girder_worker._test_plugins.plugins:TestPluginInvalidModule', # noqa
            'invalid = girder_worker._test_plugins.plugins:NotAValidClass'
        ]
    }
)
