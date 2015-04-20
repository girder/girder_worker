Developer documentation
=======================

This section of the documentation is meant for those who wish to contribute to
the Romanesco core platform.

Creating a new release
----------------------

Romanesco releases are uploaded to `PyPI <https://pypi.python.org/pypi/romanesco>`_
for easy installation via ``pip``. The recommended process for generating a new
release is described here.

1.  From the target commit, set the desired version number in ``plugin.json``.
    Create a new commit and note the SHA; this will become the release tag.

2.  Ensure that all tests pass.

3.  Clone the repository in a new directory and checkout the release SHA.
    (Packaging in an old directory could cause extraneous files to be
    mistakenly included in the source distribution.)

4.  Run ``python setup.py sdist --dist-dir .`` to generate the distribution
    tarball in the project directory, which looks like ``romanesco-x.y.z.tar.gz``.

5.  Create a new virtual environment and install the python package into
    it. This should not be done in the repository directory because the wrong package
    will be imported.  ::

        mkdir test && cd test
        virtualenv release
        source release/bin/activate
        pip install ../romanesco-<version>.tar.gz

6.  Once that finishes, you should be able to start the worker by simply running
    ``romanesco-worker``.

7.  When you are confident everything is working correctly, generate
    a `new release <https://github.com/Kitware/romanesco/releases/new>`_
    on GitHub.  You must be
    sure to use a tag version of ``v<version>``, where ``<version>``
    is the version number as it exists in ``plugin.json``.  For
    example, ``v0.2.4``.  Attach the three tarballs you generated
    to the release.

8.  Add the tagged version to `readthedocs <https://readthedocs.org/projects/romanesco/>`_
    and make sure it builds correctly.

9.  Finally, upload the release to PyPI with the following command: ::

        python setup.py sdist upload

.. note :: The first time you create a release, you will need to register to PyPI
    before you can run the upload step. To do so, simply run ``python setup.py sdist regsiter``.
