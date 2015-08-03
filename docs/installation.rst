Installation
============

To install the romanesco worker on your system, we recommend using ``pip`` to
install the package. (If you wish to install from source, see the :ref:`install-from-source`
section of the developer documentation.) The following command will install the core dependencies: ::

    pip install romanesco

That will install the core romanesco library, but not the third-party dependencies for
any of its plugins. If you want to enable a set of plugins, they should be included as
extras to the pip install command. For instance, if you are planning to use the R plugin
and the spark plugin, you would run: ::

    pip install romanesco[r,spark]

You can run this command at any time to install dependencies of other plugins, even if
romanesco is already installed.

Configuration
=============

Several aspects of Romanesco's behavior are controlled via its configuration file. This
file is found within the installed package directory as ``worker.local.cfg``. If this
file does not exist, simply run: ::

    cd romanesco ; cp worker.dist.cfg worker.local.cfg

The core configuration parameters are outlined below.

  * ``celery.app_main``: The name of the celery application. Clients will need to use
    this same name to identify what app to send tasks to. It is recommended to call this
    "romanesco" unless you have a reason not to.
  * ``celery.broker``: This is the broker that celery will connect to in order to
    listen for new tasks. Celery recommends using `RabbitMQ <https://www.rabbitmq.com/>`_
    as your message broker.
  * ``romanesco.tmp_root``: Each romanesco task is given a temporary directory that
    it can use if it needs filesystem storage. This config setting points to the
    root directory under which these temporary directories will be created.
  * ``romanesco.plugins_enabled``: This is a comma-separated list of plugins that
    will be enabled at runtime, e.g. ``spark,vtk``.
  * ``romanesco.plugin_load_path``: If you have any external plugins that are not
    inside the ``romanesco/plugins`` package directory, set this value to a
    colon-separated list of directories to search for external plugins that need to
    be loaded.

.. note :: After making changes to values in the config file, you will need to
   restart the worker before the changes will be reflected.

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
