Developer documentation
=======================

.. _install-from-source:

Installing from source
----------------------

Clone from git: ::

    git clone https://github.com/Kitware/romanesco.git
    cd romanesco

Test it: ::

    python -m unittest -v tests.table_test
    python -m unittest -v tests.tree_test

Some things not working? You can install a few things so they do.
For example, install MongoDB_ and R_,
in addition to their Python bindings: ::

    pip install pymongo rpy2  # may need sudo

.. _MongoDB: http://www.mongodb.org/
.. _R: http://www.r-project.org/

You'll need to get a MongoDB server listening on localhost by running ``mongod``.

In R, you'll need to install some stuff too, currently just the ``ape`` package: ::

    install.packages("ape")

Some things depend on VTK Python bindings. Romanesco uses some features from
cutting-edge VTK,
so you'll likely need to build it from scratch (takes ~30 minutes).
First get CMake_, then do the following: ::

    git clone git://vtk.org/VTK.git
    cd VTK
    mkdir build
    cd build
    cmake .. -DVTK_WRAP_PYTHON:BOOL=ON -DBUILD_TESTING:BOOL=OFF
    make
    export PYTHONPATH=`pwd`/Wrapping/Python:`pwd`/lib
    python -c "import vtk"  # should work without an error

.. _CMake: http://www.cmake.org/

Want to run things remotely? On the client and server install celery: ::

    pip install celery

Then fire up the celery worker: ::

    python -m romanesco

On the client, run a script akin to the following example: ::

    python clients/client.py

This section of the documentation is meant for those who wish to contribute to
the Romanesco core platform.


Note on building VTK
--------------------

The VTK binaries used for testing in the .travis.yml is built in
an Ubuntu precise 64-bit VM using the following commands: ::

    # from host
    vagrant up
    vagrant ssh

    # from Vagrant guest
    sudo apt-get update
    sudo apt-get install g++ make
    wget http://www.cmake.org/files/v2.8/cmake-2.8.12.2.tar.gz
    tar xzvf cmake-2.8.12.2.tar.gz
    cd cmake-2.8.12.2
    ./bootstrap --prefix=~/cmake-2.8.12.2-precise64
    make install
    cd ~
    git clone git://vtk.org/VTK.git
    cd VTK
    mkdir build
    cd build
    ~/cmake-2.8.12.2-precise64/bin/cmake .. -DBUILD_TESTING:BOOL=OFF -DVTK_WRAP_PYTHON:BOOL=ON -DVTK_Group_Rendering:BOOL=OFF -DVTK_Group_StandAlone:BOOL=OFF -DModule_vtkCommonDataModel:BOOL=ON -DModule_vtkIOInfovis:BOOL=ON -DModule_vtkFiltersSources:BOOL=ON -DCMAKE_INSTALL_PREFIX:PATH=~/vtk-precise64
    make install
    tar czvf vtk-precise64.tar.gz ~/vtk-precise64/
    exit

    # from host
    scp -P 2222 vagrant@localhost:~/vtk-precise64-118242.tar.gz .


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
