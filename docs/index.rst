Girder Worker: A simple, flexible execution engine
==================================================

What is Girder Worker?
----------------------

Girder Worker is a Python application for generic task execution. It can be run within a
`Celery <http://docs.celeryproject.org/en/latest/index.html>`_ worker to provide a
distributed batch job execution platform.

The application can run tasks in a variety of languages and environments, including
Python, R, and Docker, all via a single Python or Celery broker interface. Tasks
can be chained together into workflows, and these workflows can actually span multiple
languages and environments seamlessly. Data flowing between tasks can be automatically
converted into a format understandable in the target environment. For example, a Python
object from a Python task can be automatically converted into an R object for an R
task at the next stage of a pipeline.

Girder Worker defines a specification that prescribes a loose coupling between a task
and its runtime inputs and outputs. That specification is described in the :doc:`api-docs`
section. This specification is language-independent and instances of the spec are best
represented by a hierarchical data format such as JSON or YAML, or an equivalent
serializable type such as a ``dict`` in Python.  Several :doc:`examples` of using
these specifications to generate tasks and workflows are provided.

Girder Worker is designed to be easily extended to new languages and environments, or
to support new data types and formats, or modes of data transfer. This is accomplished
via its plugin system, which is described in :doc:`plugins`.

.. toctree::
   :maxdepth: 2

   installation
   types-and-formats
   api-docs
   examples
   developer-docs
   plugins
   docker_run

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
