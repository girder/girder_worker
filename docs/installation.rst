Installation
************

To install the Girder Worker on your system, we recommend using ``pip`` to
install the package. ::

    pip install girder-worker

That will install the core girder-worker library and the built-in :ref:`plugins`.



.. _remoteexecution:

Remote Execution
================


Configuration
=============

Several aspects of the worker's behavior are controlled via its configuration file. The easiest
way to manage configuration is using the ``girder-worker-config`` command that is installed
with the package. After installation, run  ::

    $ girder-worker-config --help

You should see the list of available sub-commands for reading and writing config values.
To show all configuration options, run ::

    $ girder-worker-config list

To set a specific option, use ::

    $ girder-worker-config set <section_name> <option_name> <value>

For example: ::

    $ girder-worker-config set celery broker amqp://me@localhost/

To change a setting back to its default value, use the ``rm`` subcommand ::

    $ girder-worker-config rm celery broker

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
    will be enabled at runtime, e.g. ``r,docker``.
  * ``girder_worker.plugin_load_path``: If you have any external plugins that are not
    inside the **girder_worker/plugins** package directory, set this value to a
    colon-separated list of directories to search for external plugins that need to
    be loaded.

.. note :: After making changes to values in the config file, you will need to
   restart the worker before the changes will be reflected.

.. note :: Some projects have reported issues with connection pool dropping 
   when using Celery 4.2 and 4.3.  If you see an error 
   ``ConnectionResetError(104, 'Connection reset by peer')``, try using 
   Celery < 4.2 or >= 4.4.0rc3.  See `Celery issue 4867 
   <https://github.com/celery/celery/issues/4867>`_.
   
