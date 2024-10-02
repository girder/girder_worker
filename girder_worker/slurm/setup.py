from setuptools import find_packages, setup

with open('requirements.txt') as f:
    install_reqs = f.readlines()

setup(
    name='girder-worker-slurm',
    version='0.0.0',
    description='An example girder worker extension',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    license='Apache Software License 2.0',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    install_requires=['girder-worker', 'girder-worker-singularity', *install_reqs],
    entry_points={
        'girder.plugin': [
            'worker_slurm = girder_worker_slurm.girder_plugin:WorkerSlurmPlugin',
        ],
    },
    packages=find_packages(),
    zip_safe=False
)
