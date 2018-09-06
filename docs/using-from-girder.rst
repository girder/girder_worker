Using Girder Worker with Girder
*******************************

The most common use case of Girder Worker is running processing tasks on
data managed by a Girder server. Typically, either a user action or an automated
process running on the Girder server initiates the execution of a task that
runs on a Girder Worker.

The task to be run must be installed in both the Girder server environment as well as the
worker environment. If you are using a built-in plugin, you can just install
girder-worker on the Girder server environment. If you're using a custom task
plugin, ``pip install`` it on both the workers and the Girder server environment.

Running tasks as Girder jobs
----------------------------

Once installed, starting a job is as simple as importing the task into the python environment
and calling `delay()` on it. The following example assumes your task exists in a package
called ``my_worker_tasks``:

.. code-block:: python

    from my_worker_tasks import my_task

    result = my_task.delay(arg1, arg2, kwarg1='hello', kwarg2='world')

Here the ``result`` variable is a `celery result object <http://docs.celeryproject.org/en/latest/reference/celery.result.html>`_
with Girder-specific properties attached. Most importantly, it contains a ``job`` attribute
that is the created job document associated with this invocation of the task. That job will
be owned by the user who initiated the request, and Girder worker will automatically update its
status according to the task's execution state. Additionally, any standard output or standard
error data will be automatically added to the log of that job. You can also set fields on the job
using the `delay` method kwargs ``girder_job_title``, ``girder_job_type``, ``girder_job_public``,
and ``girder_job_other_fields``. For instance, to set the title and type of the created job:

.. code-block:: python

    job = my_task.delay(girder_job_title='This is my job', girder_job_type='my_task')
    assert job['title'] == 'This is my job'
    assert job['type'] == 'my_task'


Downloading files from Girder for use in tasks
----------------------------------------------

.. note:: This section applies to python tasks, if you are using the built-in ``docker_run`` task,
          it has its own set of transforms for dealing with input and output data, which are
          detailed in the :ref:`docker-run` documentation

The following example makes use of a Girder Worker transform for passing a Girder file into
a Girder Worker task. The
:py:class:`girder_worker_utils.transforms.girder_io.GirderFileId` transform causes the file
with the given ID to be downloaded locally to the worker node, and its local path will then
be passed into the function in place of the transform object. For example:

.. code-block:: python

    from girder_worker_utils.transforms.girder_io import GirderFileId

    def process_file(file):
        return my_task.delay(input_file=GirderFileId(file['_id'])).job
