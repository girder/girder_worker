from setuptools import setup, find_packages

setup(name='gwexample',
      version='0.0.0',
      description='An example girder worker extension',
      author='Chris Kotfila',
      author_email='chris.kotfila@kitware.com',
      license='Apache v2',
      classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'License :: OSI Approved :: Apache Software License'
          'Topic :: Scientific/Engineering :: GIS',
          'Intended Audience :: Science/Research',
          'Natural Language :: English',
          'Programming Language :: Python'
      ],
      entry_points={
          'girder_worker_plugins': [
              'gwexample = gwexample:GWExamplePlugin',
          ]
      },
      packages=find_packages(),
      zip_safe=False)
