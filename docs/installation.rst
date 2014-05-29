Installation
============

TBD

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
