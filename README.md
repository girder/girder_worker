cardoon
=======

A flexible, dead-simple script execution engine.

Get Started
===========

Get it.
```
git clone https://github.com/arborworkflows/cardoon.git
cd cardoon
```

Test it.
```
python -m unittest -v tests.table_test
python -m unittest -v tests.tree_test
```

Some things not working? You can install a few things so they do.
For example, install [MongoDB](http://www.mongodb.org/) and [R](http://www.r-project.org/) and their Python bindings:
```
pip install pymongo rpy2  # may need sudo
```
You'll need to get MongoDB server listening on localhost with `mongod`.

Some things depend on VTK Python bindings. You'll likely need to build it from scratch (takes ~30 mintues).
First get [CMake](http://www.cmake.org/), then do the following:
```
wget http://www.vtk.org/files/release/6.1/VTK-6.1.0.tar.gz
tar xzvf VTK-6.1.0.tar.gz
cd VTK-6.1.0
mkdir build
cd build
cmake .. -DVTK_WRAP_PYTHON:BOOL=ON
make
export PYTHONPATH=`pwd`/Wrapping/Python:`pwd`/lib
```

Want to run things remotely? On the server:
```
python -m cardoon
```

On the client:
```
python clients/client.py
```
