Getting Started
***************

Choosing a Broker
=================

The first step in getting Girder Worker up and running is installing a `broker <http://docs.celeryproject.org/en/latest/getting-started/first-steps-with-celery.html#choosing-a-broker>`_. The broker is a message queue such as `RabbitMQ <https://www.rabbitmq.com/>`_ which receives messages and passes them to workers to execute a task. If you are running on an Ubuntu or Debian server you can install RabbitMQ with the following command ::

  $ sudo apt-get install rabbitmq-server

Alternately, if you have docker installed,  you can run the rabbitmq inside a container ::

  $ docker run --net=host -d rabbitmq:latest

Installing Girder Worker
========================

Girder Worker is a python package and may be installed with pip ::

  $ pip install girder-worker[girder]

We recommend installing in a virtual environment to prevent package
collision with your system Python.

.. _creating-task-plugin:

Creating a Task Plugin
======================

Task plugins are python packages. Multiple tasks may be placed in the same package but they must be installed in your environment to be discovered. Python packages require a certain amount of boilerplate to get started. The easiest way to create a package with a task plugin is to use the `cookiecutter <https://cookiecutter.readthedocs.io/en/latest/>`_ tool along with the `Girder Worker plugin cookiecutter template <https://github.com/girder/cookiecutter-gw-plugin>`_.

First install cookiecutter ::

  $ pip install cookiecutter

Next generate a task plugin Python package ::

  $ cookiecutter gh:girder/cookiecutter-gw-plugin

This will prompt you with a number of questions about the package. For now you can simply select the defaults by hitting ``Enter``. This should create a ``gw_task_plugin`` folder in your current working directory.

Adding Task Code
----------------

Open the ``gw_task_plugin/gw_task_plugin/tasks.py`` file. You will find the following code.

.. code-block:: python

   from girder_worker.app import app
   from girder_worker.utils import girder_job

   # TODO: Fill in the function with the correct argument signature
   # and code that performs the task.
   @girder_job(title='Example Task')
   @app.task(bind=True)
   def example_task(self):
       pass

Edit example_task function to return the value "Hello World!".

Installing the Task Plugin
==========================

The cookiecutter template has created a barebones Python package which can now be installed with pip.  Return to the folder with the outermost ``gw_task_plugin`` folder and install the package ::

  $ pip install gw_task_plugin/

Running the Worker
==================

Now run the worker from a command line ::

  $ celery worker -A girder_worker.app -l info

If all is well,  you should see a message similar to the following ::

   -------------- celery@isengard v4.1.0 (latentcall)
   ---- **** -----
   --- * ***  * -- Linux-4.15.5-1-ARCH-x86_64-with-glibc2.2.5 2018-02-27 19:28:07
   -- * - **** ---
   - ** ---------- [config]
   - ** ---------- .> app:         girder_worker:0x7f72fd800ed0
   - ** ---------- .> transport:   amqp://guest:**@localhost:5672//
   - ** ---------- .> results:     amqp://
   - *** --- * --- .> concurrency: 4 (prefork)
   -- ******* ---- .> task events: OFF (enable -E to monitor tasks in this worker)
   --- ***** -----
    -------------- [queues]
                   .> celery           exchange=celery(direct) key=celery


   [tasks]
     . girder_worker.docker.tasks.docker_run
     . gw_task_plugin.tasks.example_task

   [2018-02-27 19:28:07,205: INFO/MainProcess] Connected to amqp://guest:**@127.0.0.1:5672//
   [2018-02-27 19:28:07,226: INFO/MainProcess] mingle: searching for neighbors
   [2018-02-27 19:28:08,266: INFO/MainProcess] mingle: all alone
   [2018-02-27 19:28:08,321: INFO/MainProcess] celery@isengard ready.


As long as ``gw_task_plugin.tasks.example_task`` is listed under the ``[tasks]`` section then you are ready to move on to the next section.

Executing the Task
==================
In a separate terminal,  open up a python shell and type the following: ::

    $ python

Import the task: ::

    >>> from gw_task_plugin.tasks import example_task

Execute the task asynchronously: ::

    >>> a = example_task.delay()
    >>> a.get()
    u'Hello World!'

Wrapping Up
===========

In this tutorial we briefly demonstrated how to:

+ Install and run a broker
+ Install Girder Worker
+ Create and install a task plugin
+ Execute the task remotely with a Python interpreter

The goal here was to get up and running as quickly as possible and so each of these topics has been treated lightly.


+ Celery supports a few different brokers. For more information see Celery's complete `broker documentation <http://docs.celeryproject.org/en/latest/getting-started/brokers/index.html>`_.
+ Task plugin Python packages do more than just add a ``setup.py`` and create a ``tasks.py`` for dumping tasks into. For more information on what the boilerplate the cookiecutter created see :doc:`plugins`.
+ Girder Worker aims to provide task execution API that is exactly the same as Celery. For more information on calling tasks see Celery's `Calling Tasks <http://docs.celeryproject.org/en/latest/getting-started/next-steps.html#calling-tasks>`_ documentation. For more information about the knobs and dials available for changing how task execute, see Celery's `Task <http://docs.celeryproject.org/en/latest/userguide/tasks.html>`_ documentation.

Finally,  we *highly* recommend reading through the Celery's `First Steps with Celery <http://docs.celeryproject.org/en/latest/getting-started/first-steps-with-celery.html>`_ documentation as well as their `User Guide <http://docs.celeryproject.org/en/latest/userguide/index.html#guide>`_. For some important differences between Celery and Girder Worker,  we recommend keeping the :doc:`important-differences` page open while working through Celery's documentation.
