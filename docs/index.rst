Girder Worker: A simple, flexible execution engine
**************************************************

Girder Worker is a remote task execution engine designed to work with
`Girder <https://girder.readthedocs.io/en/latest/index.html>`_. Girder
Worker provides a thin wrapper around `Celery
<http://docs.celeryproject.org/en/latest/index.html>`_ which is an
asynchronous task queue/job queue based on distributed message
passing. Girder Worker relies heavily on Celery for its API and
implementation, adding two critical features:

- **Task Discovery** Girder Worker implements a custom mechanism for discovering installed tasks at run time. These "pluggable" tasks are defined as python packages and installed in the environment where Girder Worker is run.
- **Task Tracking**  If called from Girder, Girder Worker generates a Girder `Job <https://girder.readthedocs.io/en/latest/plugins.html#jobs>`_ for tracking task status and getting real-time output of job progress. If *not* called from Girder, Girder Worker reverts to traditional Celery behavior, making it amenable to running tasks in a python interpreter, scripts, or `Jupyter Notebooks <https://jupyter-notebook.readthedocs.io/en/stable/>`_.

.. toctree::
   :maxdepth: 1

   getting-started
   installation
   plugins
   builtin-plugins
   using-from-girder
   developer-docs
   api-docs
   important-differences
..   installation
..   types-and-formats

..   examples
..   developer-docs

..   docker_run

Indices and tables

==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
