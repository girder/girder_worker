Installation
============

To install the Girder Worker on your system, we recommend using ``pip`` to
install the package. (If you wish to install from source, see the :ref:`install-from-source`
section of the developer documentation.)

First, install required system packages: ::

    # Command for Ubuntu
    sudo apt-get install libjpeg-dev zlib1g-dev

Next, the following command will install the core dependencies: ::

    pip install girder-worker

That will install the core girder-worker library, but not the third-party dependencies for
any of its plugins. If you want to enable a set of plugins, their IDs should be included as
extras to the pip install command. For instance, if you are planning to use the R plugin
and the spark plugin, you would run: ::

    pip install girder-worker[r,spark]

You can run this command at any time to install dependencies of other plugins, even if
the girder worker is already installed.

.. _configuration:

Configuration
-------------

Several aspects of the worker's behavior are controlled via its configuration file. This
file is found within the installed package directory as ``worker.local.cfg``. If this
file does not exist, simply run: ::

    cd girder_worker ; cp worker.dist.cfg worker.local.cfg

The core configuration parameters are outlined below.

  * ``celery.app_main``: The name of the celery application. Clients will need to use
    this same name to identify what app to send tasks to. It is recommended to call this
    "girder_worker" unless you have a reason not to.
  * ``celery.broker``: This is the broker that celery will connect to in order to
    listen for new tasks. Celery recommends using `RabbitMQ <https://www.rabbitmq.com/>`_
    as your message broker.
  * ``girder_worker.tmp_root``: Each task is given a temporary directory that
    it can use if it needs filesystem storage. This config setting points to the
    root directory under which these temporary directories will be created.
  * ``girder_worker.plugins_enabled``: This is a comma-separated list of plugin IDs that
    will be enabled at runtime, e.g. ``spark,vtk``.
  * ``girder_worker.plugin_load_path``: If you have any external plugins that are not
    inside the **girder_worker/plugins** package directory, set this value to a
    colon-separated list of directories to search for external plugins that need to
    be loaded.

.. note :: After making changes to values in the config file, you will need to
   restart the worker before the changes will be reflected.
