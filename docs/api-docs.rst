API documentation
=================

Overview
--------

The main purpose of Romanesco is to execute a broad range of tasks. These tasks,
along with a set of input bindings and output bindings are passed to the :py:func:`romanesco.run`
function, which is responsible for fetching the inputs as necessary and executing
the task, and finally populating any output variables and sending them to their
destination.

The task, its inputs, and its outputs are each passed into the function as python dictionaries.
In this section, we describe the structure of each of those dictionaries.

The task specification
**********************

The first argument to :py:func:`romanesco.run` describes the task to execute,
independently of the actual data that will it will be executed against. The most
important field of the task is the ``mode``, which describes what type of task
this is. The structure for the task dictionary is described below. Uppercase names
within angle braces represent symbols defined in the specification. Optional parts
of the specification are surrounded by parenthesis to avoid ambiguity with the
square braces, which represent lists in python or Arrays in JSON.

.. code-block :: none

    <TASK> ::= <PYTHON_TASK> | <R_TASK> | <DOCKER_TASK> | <WORKFLOW_TASK>

    <PYTHON_TASK> ::= {
        "mode": "python",
        "script": <python code to run as a string>
        (, "inputs": [<TASK_INPUT> (, <TASK_INPUT>, ...)])
        (, "outputs": [<TASK_OUTPUT> (, <TASK_OUTPUT>, ...)])
    }

    <R_TASK> ::= {
        "mode": "r",
        "script": <r code to run (as a string)>
        (, "inputs": [<TASK_INPUT> (, <TASK_INPUT>, ...)])
        (, "outputs": [<TASK_OUTPUT> (, <TASK_OUTPUT>, ...)])
    }

    <DOCKER_TASK> ::= {
        "mode": "docker",
        "docker_image": <docker image name to run>
        (, "container_args": [<container arguments>])
        (, "inputs": [<TASK_INPUT> (, <TASK_INPUT>, ...)])
        (, "outputs": [<TASK_OUTPUT> (, <TASK_OUTPUT>, ...)])
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
specified to :py:func:`romanesco.run`.

.. code-block:: none

    <TASK_INPUT> ::= {
        "id": <string, the variable name>,
        "type": <data type>,
        "format": <data format>
        (, "target": <INPUT_TARGET_TYPE>)   ; default is "memory"
        (, "filename": <name of file if target="filepath">)
    }

    <INPUT_TARGET_TYPE> ::= "memory" | "filepath"

    <TASK_OUTPUT> ::= {
        "id": <string, the variable name>,
        "type": <data type>,
        "format": <data format>
        (, "target": <INPUT_TARGET_TYPE>)   ; default is "memory"
    }


The input specification
***********************

The ``inputs`` argument to :py:func:`romanesco.run` specifies the inputs to the
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

The output specification
************************

The optional ``outputs`` argument to :py:func:`romanesco.run` specifies output
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
return value of :py:func:`romanesco.run`.

.. code-block:: none

    <OUTPUT_BINDING> ::= <OUTPUT_BINDING_HTTP> | <OUTPUT_BINDING_LOCAL> |
                         <OUTPUT_BINDING_MONGODB>

    <OUTPUT_BINDING_HTTP> ::= {
        "mode": "http",
        "url": <url to upload data to>,
        "format": <data format>
        (, "headers": <dict of HTTP headers to send with the request>)
        (, "method": <http method to use, default is "POST">)
    }

    <OUTPUT_BINDING_LOCAL> ::= {
        "mode": "local",
        "format": <data format>
        "path": <path to write data on the local filesystem>
    }

The local output mode writes the data to the specified path on the local filesystem.

.. code-block:: none

    <OUTPUT_BINDING_MONGODB> ::= {
        "mode": "mongodb",
        "db": <mongo database to write to>,
        "format": <data format>
        "collection": <mongo collection to write to>
        (, "host": <mongo host to connect to>)
    }

The mongodb output mode attempts to BSON-decode the bound data, and then overwrites
any data in the specified collection with the output data.


Script execution
----------------

.. automodule:: romanesco
   :members:

Formats
-------

.. automodule:: romanesco.format
   :members:

URIs
----

.. automodule:: romanesco.uri
   :members:
