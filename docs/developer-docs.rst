Developer documentation
=======================

This section of the documentation is meant for those who wish to contribute to
the Girder Worker platform.

.. _install-from-source:

Installing from source
----------------------

Clone from git: ::

    git clone https://github.com/girder/girder_worker.git
    cd girder_worker

Install requirements: ::

    pip install -r requirements.txt

    # If you plan on developing the worker, you will also want to install system packages and Python requirements:

    # Command for Ubuntu
    sudo apt-get install libxml2-dev libxslt1-dev

    pip install -r requirements-dev.txt

If you want to run the girder_worker as a remote worker from the source install directory, you'll need to install it with pip in editable mode. If you don't want to include
any girder worker plugins: ::

    pip install -U -e .

Test it: ::

To test whether the setup without complex dependencies is working

    python -m unittest tests.format_test

To test the setup is working with complex dependencies including R and Mongo

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

.. _CMake: http://www.cmake.org/

Installing worker plugins from pip
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

An individual plugin can be installed through pip, in editable mode, like so: ::

    pip install -U -e .[r]

You can run this command at any time to install dependencies of other plugins, even if
the worker is already installed.

.. seealso::

   For more information on the worker plugin system, see :doc:`plugins`.


Creating a new release
----------------------

Girder Worker releases are uploaded to `PyPI <https://pypi.python.org/pypi/girder-worker>`_
for easy installation via ``pip``. The recommended process for generating a new
release is described here.

1.  From the target commit, set the desired version number in the top level ``__init__.py``.
    Create a new commit and note the SHA; this will become the release tag.

2.  Ensure that all tests pass.

3.  Clone the repository in a new directory and checkout the release SHA.
    (Packaging in an old directory could cause extraneous files to be
    mistakenly included in the source distribution.)

4.  Run ``python setup.py sdist --dist-dir .`` to generate the distribution
    tarball in the project directory, which looks like ``girder-worker-x.y.z.tar.gz``.

5.  Create a new virtual environment and install the Python package into
    it. This should not be done in the repository directory because the wrong package
    will be imported.  ::

        mkdir test && cd test
        virtualenv release
        source release/bin/activate
        pip install ../girder-worker-<version>.tar.gz

6.  Once that finishes, you should be able to start the worker by simply running
    ``girder-worker``.

7.  When you are confident everything is working correctly, generate
    a `new release <https://github.com/girder/girder-worker/releases/new>`_
    on GitHub.  You must be
    sure to use a tag version of ``v<version>``, where ``<version>``
    is the version number as it exists in ``setup.py``.  For
    example, ``v0.2.4``.  Attach the tarball you generated to the release.

8.  Add the tagged version to `readthedocs <https://readthedocs.org/projects/girder_worker/>`_
    and make sure it builds correctly.

9.  Finally, upload the release to PyPI with the following command: ::

        python setup.py sdist upload

.. note :: The first time you create a release, you will need to register to PyPI
    before you can run the upload step. To do so, simply run ``python setup.py sdist register``.


.. _task-plugins:

Task Plugins
============================

This is an example plugin that demonstrates how to extend girder\_worker
by allowing it to run additional tasks. Plugin's are implemented as
separate pip installable packages. To install this example plugin you
can checkout this code base, change directories to
``examples/plugin_example/`` and run ``pip install .`` This will add the
``gwexample`` plugin to girder\_worker. If you then run girder\_worker
with a log level of 'info' (e.g. ``girder-worker -l info``) you should
see the following output:

::

    (girder)$ girder-worker -l info

     -------------- celery@minastirith v3.1.23 (Cipater)
    ---- **** -----
    --- * ***  * -- Linux-4.8.6-1-ARCH-x86_64-with-glibc2.2.5
    -- * - **** ---
    - ** ---------- [config]
    - ** ---------- .> app:         girder_worker:0x7f69bfff1050
    - ** ---------- .> transport:   amqp://guest:**@localhost:5672//
    - ** ---------- .> results:     amqp://
    - *** --- * --- .> concurrency: 32 (prefork)
    -- ******* ----
    --- ***** ----- [queues]
     -------------- .> celery           exchange=celery(direct) key=celery


    [tasks]
      . girder_worker.convert
      . girder_worker.run
      . girder_worker.validators
      . gwexample.analyses.tasks.fibonacci

    [2016-11-08 12:22:56,163: INFO/MainProcess] Connected to amqp://guest:**@127.0.0.1:5672//
    [2016-11-08 12:22:56,184: INFO/MainProcess] mingle: searching for neighbors
    [2016-11-08 12:22:57,198: INFO/MainProcess] mingle: all alone
    [2016-11-08 12:22:57,218: WARNING/MainProcess] celery@minastirith ready.

Notice that the task ``gwexample.analyses.tasks.fibonacci`` is now
available. With the girder-worker processes running, you should be able to
execute ``python example_client.py`` in the current working directory.
After a brief delay, this should print out ``121393`` - the Fibonacci
number for 26.

Writing your own plugin
-----------------------

Adding additional tasks to the girder\_worker infrastructure is easy and
takes three steps. (1) Creating tasks, (2) creating a plugin class and
(3) adding a ``girder_worker_plugins`` entry point to your setup.py.

Creating tasks
~~~~~~~~~~~~~~

Creating tasks follows the standard `celery
conventions <http://docs.celeryproject.org/en/latest/userguide/tasks.html>`__.
The only difference is the celery application that decorates the
function should be imported from ``girder_worker.app``. E.g.:

.. code:: python

    from girder_worker.app import app

    @app.task
    def fibonacci(n):
        if n == 1 or n == 2:
            return 1
        return fibonacci(n-1) + fibonacci(n-2)

Plugin Class
~~~~~~~~~~~~

Each plugin must define a plugin class the inherits from
``girder_worker.GirderWorkerPluginABC``. GirderWorkerPluginABC's
interface is simple. The class must define an ``__init__`` function and
a ``task_imports`` function. ``__init__`` takes the girder\_worker's
celery application as its first argument. This allows the plugin to
store a reference to the application, or change configurations of the
application as necessary. The ``task_imports`` function takes no
arguments and must return a list of the package paths (e.g. importable
strings) that contain the plugin's tasks. As an example:

.. code:: python

    from girder_worker import GirderWorkerPluginABC

    class GWExamplePlugin(GirderWorkerPluginABC):
        def __init__(self, app, *args, **kwargs):
            self.app = app

            # Update the celery application's configuration
            # it is not necessary to change the application configuration
            # this is simply included to illustrate that it is possible.
            self.app.config.update({
                'TASK_TIME_LIMIT': 300
            })

        def task_imports(self):
            return ['gwexample.analyses.tasks']

Entry Point
~~~~~~~~~~~

Finally, in order to make the plugin class discoverable, each plugin
must define a custom entry point in its ``setup.py``. For our example,
this entry point looks like this:

.. code:: python

    from setuptools import setup

    setup(name='gwexample',
          # ....
          entry_points={
              'girder_worker_plugins': [
                  'gwexample = gwexample:GWExamplePlugin',
              ]
          },
          # ....
          )

Python `Entry
Points <https://setuptools.readthedocs.io/en/latest/pkg_resources.html#entry-points>`__
are a way for python packages to advertise classes and objects to other
installed packages. Entry points are defined in the following way:

.. code:: python

        entry_points={
            'entry_point_group_id': [
                'entry_point_name = importable.package.name:class_or_object',
            ]
        }

The girder\_worker package introduces a new entry point group
``girder_worker_plugins``. This is followed by a list of strings which
are parsed by setuptools. The strings must be in the form
``name = module:plugin_class`` Where ``name`` is an arbitrary string (by
convention the name of the plugin), ``module`` is the importable path to
the module containing the plugin class, and ``plugin_class`` is a class
that inherits from ``GirderWorkerPluginABC``.

Final notes
-----------

With these three components (Tasks, Plugin Class, Entry Point) you
should be able to add arbitrary tasks to the girder\_worker client. By
default, jobs created in girder using the 'worker' plugin run the
``girder_worker.run`` task. This can be overridden to call custom plugin
tasks by generating jobs with a ``celeryTaskName`` defined in the job's
``otherFields`` key word argument. E.g.:

.. code:: python


    # Create a job to be handled by the worker plugin
    job = jobModel.createJob(
        title='Some Job', type='some_type', handler='worker_handler',
        user=self.admin, public=False, args=(25), kwargs={},
        otherFields={
            'celeryTaskName': 'gwexample.analyses.tasks.fibonacci'
        })

    jobModel.scheduleJob(job)

This will schedule a job that runs
``gwexample.analyses.tasks.fibonacci(25)`` on the girder worker.

Finally, by default the core girder\_worker tasks (``run``, ``convert``,
``validate``) are included along with their plugins etc. If you wish to
prevent these tasks from being loaded inside the celery instance, you
can configure ``core_tasks=false`` in ``worker.local.cfg`` under the
``[girder_worker]`` section of the configuration.

Writing cancelable tasks
========================

girder_worker provides support for signaling that a task should be canceled using
Celery's `revoke <http://docs.celeryproject.org/en/latest/userguide/workers.html#revoke-revoking-tasks>`_
mechanism. In order for a task to be able to be canceled cleanly it must periodically
check if it has been canceled, if it has then is can do any necessary cleanup and
return. girder_worker provides a task base class (``girder_worker.utils.Task`` )
that provides a property that can be used to check if the task has been canceled.
An example of its use is shown below:


.. code:: python

    from girder_worker.app import app
    from girder_work.utils import Task

    @app.task(bind=True)
    def my_cancellable_task(task):
      while not self.cancelled:
         # Do work

The Girder job model associated with the canceled task will be moved into the
``JobStatus.CANCELED`` state.
