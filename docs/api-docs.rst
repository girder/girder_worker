API documentation
=================

Overview
--------

The main purpose of Girder Worker is to execute a broad range of tasks. These tasks,
along with a set of input bindings and output bindings are passed to the :py:func:`girder_worker.tasks.run`
function, which is responsible for fetching the inputs as necessary and executing
the task, and finally populating any output variables and sending them to their
destination.

The task, its inputs, and its outputs are each passed into the function as Python dictionaries.
In this section, we describe the structure of each of those dictionaries.

The task specification
**********************

The first argument to :py:func:`girder_worker.tasks.run` describes the task to execute,
independently of the actual data that it will be executed upon. The most
important field of the task is the ``mode``, which describes what type of task
it is. The structure for the task dictionary is described below. Uppercase names
within angle braces represent symbols defined in the specification. Optional parts
of the specification are surrounded by parentheses to avoid ambiguity with the
square braces, which represent lists in Python or Arrays in JSON. The Python task
also accepts a ``write_script`` parameter that when set to 1 will write task scripts to
disk before executing them.  This aids in readability for interactive debuggers
such as ``pdb``.

.. code-block :: none

    <TASK> ::= <PYTHON_TASK> | <R_TASK> | <DOCKER_TASK> | <WORKFLOW_TASK>

    <PYTHON_TASK> ::= {
        "mode": "python",
        "script": <Python code to run as a string>
        (, "inputs": [<TASK_INPUT> (, <TASK_INPUT>, ...)])
        (, "outputs": [<TASK_OUTPUT> (, <TASK_OUTPUT>, ...)])
        (, "write_script": 1)
    }

    <R_TASK> ::= {
        "mode": "r",
        "script": <R code to run (as a string)>
        (, "inputs": [<TASK_INPUT> (, <TASK_INPUT>, ...)])
        (, "outputs": [<TASK_OUTPUT> (, <TASK_OUTPUT>, ...)])
    }

    <DOCKER_TASK> ::= {
        "mode": "docker",
        "docker_image": <Docker image name to run>
        (, "container_args": [<container arguments>])
        (, "entrypoint": <custom override for container entry point>)
        (, "inputs": [<TASK_INPUT> (, <TASK_INPUT>, ...)])
        (, "outputs": [<TASK_OUTPUT> (, <TASK_OUTPUT>, ...)])
        (, "progress_pipe": <set to true to create a channel for progress notifications>)
    }

    <WORKFLOW_TASK> ::= {
        "mode": "workflow",
        "steps": [<WORKFLOW_STEP> (, <WORKFLOW_STEP>, ...)],
        "connections": [<WORKFLOW_CONNECTION> (, <WORKFLOW_CONNECTION>, ...)]
        (, "inputs": [<TASK_INPUT> (, <TASK_INPUT>, ...)])
        (, "outputs": [<TASK_OUTPUT> (, <TASK_OUTPUT>, ...)])
    }

    <WORKFLOW_STEP> ::= {
        "name": <step name>,
        "task": <TASK>
    }

    <WORKFLOW_CONNECTION> ::= {
        ("name": <name of top-level input to bind to>)
        (, "input": <input id to bind to for a step>)
        (, "input_step": <input step name to connect>)
        (, "output_step": <output step name to connect>)
    }

The workflow mode simply allows for a directed acyclic graph of tasks to be
specified to :py:func:`girder_worker.run`.

.. seealso::

   Visualize Facebook data with Girder Worker in :doc:`examples`
      A full example of how to create workflows in Girder Worker.

.. code-block:: none

    <TASK_INPUT> ::= {
        "id": <string, the variable name>
        (, "default": <default value if none is bound at runtime>)
        (, "target": <INPUT_TARGET_TYPE>)   ; default is "memory"
        (, "filename": <name of file if target="filepath">)
        (, "stream": <set to true to indicate a streaming input>)
    }

    <INPUT_TARGET_TYPE> ::= "memory" | "filepath"

    <TASK_OUTPUT> ::= {
        "id": <string, the variable name>,
        (, "target": <INPUT_TARGET_TYPE>)   ; default is "memory"
        (, "stream": <set to true to indicate a streaming output>)
    }

.. _input-spec:

The input specification
***********************

The ``inputs`` argument to :py:func:`girder_worker.run` specifies the inputs to the
task described by the ``task`` argument. Specifically, it tells what data should
be placed into the task input ports.

.. code-block:: none

    <INPUTS> ::= {
        <id> : <INPUT_BINDING>
        (, <id> : <INPUT_BINDING>)
        (, ...)
    }

The input spec is a dictionary mapping each ``id`` (corresponding to the ``id`` key of
each task input) to its data binding for this execution.

.. code-block:: none

    <INPUT_BINDING> ::= <INPUT_BINDING_HTTP> | <INPUT_BINDING_LOCAL> |
                        <INPUT_BINDING_MONGODB> | <INPUT_BINDING_INLINE>

    <INPUT_BINDING_HTTP> ::= {
        "mode": "http",
        "url": <url of data to download>
        (, "params": <dict of URL parameters to encode>)
        (, "headers": <dict of HTTP headers to send when fetching>)
        (, "method": <http method to use, default is "GET">)
        (, "maxSize": <integer, max size of download in bytes>)
    }

The http input mode specifies that the data should be fetched over HTTP. Depending
on the ``target`` field of the corresponding task input specifier, the data will
either be passed in memory, or streamed to a file on the local filesystem, and the
variable will be set to the path of that file.

.. code-block:: none

    <INPUT_BINDING_LOCAL> ::= {
        "mode": "local",
        "path": <path on local filesystem to the file>
    }

The local input mode denotes that the data exists on the local filesystem. Its
contents will be read into memory and the variable will point to those contents.

.. code-block:: none

    <INPUT_BINDING_MONGODB> ::= {
        "mode": "mongodb",
        "db": <the database to use>,
        "collection": <the collection to fetch from>
        (, "host": <mongodb host, default is "localhost">)
    }

The mongodb input mode specifies that the data should be fetched from a mongo
collection. This simply binds the entire BSON-encoded collection to the input
variable.

.. code-block:: none

    <INPUT_BINDING_INLINE> ::= {
        "mode": "inline",
        "data": <data to bind to the variable>
    }

The inline input mode simply passes the data directly in the input binding dictionary
as the value of the "data" key. Do not use this for any data that could be large.

*Note:* The ``mode`` field is inferred in a few special cases. If there is a ``url`` field,
the ``mode`` is assumed to be ``"http"``, and if there is a ``data`` field, the ``mode``
is assumed to be ``"inline"``. For example, the following input specifications
are equivalent:

.. code-block:: none

    {
        'url': 'https://upload.wikimedia.org/wikipedia/en/2/24/Lenna.png'
    }

.. code-block:: none

    {
        'mode': 'http',
        'url': 'https://upload.wikimedia.org/wikipedia/en/2/24/Lenna.png'
    }

The following two specifications are also equivalent:

.. code-block:: none

    {
        'data': 'hello'
    }

.. code-block:: none

    {
        'mode': 'inline',
        'data': 'hello'
    }

The output specification
************************

The optional ``outputs`` argument to :py:func:`girder_worker.run` specifies output
variables of the task that should be handled in some way.

.. code-block:: none

    <OUTPUTS> ::= {
        <id> : <OUTPUT_BINDING>
        (, <id> : <OUTPUT_BINDING>)
        (, ...)
    }

The output spec is a dictionary mapping each ``id`` (corresponding to the ``id`` key of
each task output) to some behavior that should be performed with it. Task outputs
that do not have bindings in the ouput spec simply get their results set in the
return value of :py:func:`girder_worker.run`.

.. code-block:: none

    <OUTPUT_BINDING> ::= <OUTPUT_BINDING_HTTP> | <OUTPUT_BINDING_LOCAL> |
                         <OUTPUT_BINDING_MONGODB>

    <OUTPUT_BINDING_HTTP> ::= {
        "mode": "http",
        "url": <url to upload data to>,
        (, "headers": <dict of HTTP headers to send with the request>)
        (, "method": <http method to use, default is "POST">)
        (, "params": <dict of HTTP query parameters to send with the request>)
    }

    <OUTPUT_BINDING_LOCAL> ::= {
        "mode": "local",
        "path": <path to write data on the local filesystem>
    }

The local output mode writes the data to the specified path on the local filesystem.

.. code-block:: none

    <OUTPUT_BINDING_MONGODB> ::= {
        "mode": "mongodb",
        "db": <mongo database to write to>,
        "collection": <mongo collection to write to>
        (, "host": <mongo host to connect to>)
    }

The mongodb output mode attempts to BSON-decode the bound data, and then overwrites
any data in the specified collection with the output data.


Script execution
----------------

.. automodule:: girder_worker
   :members:

Formats
-------

.. automodule:: girder_worker.plugins.types.format
   :members:

Pythonic task API
-----------------

.. automodule:: girder_worker.core.specs
   :members:
