.. Romanesco documentation master file, created by
   sphinx-quickstart on Thu Aug  8 21:34:47 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Romanesco: A simple, flexible execution engine
==============================================

.. toctree::
   :maxdepth: 2

   installation
   types-and-formats
   api-docs
   developer-docs

Romanesco is a simple, flexible execution engine
that features cross-language scripting support (currently Python and R),
automatic format conversion, and URI serialization.

Get Started
-----------

Get it: ::

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

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
