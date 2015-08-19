Plugins
=======

The Romanesco plugin system is used to extend the core functionality of Romanesco
in a number of ways. Plugins can execute any python code when they are loaded at
runtime, but the most common augmentations they perform are:

  * **Adding new execution modes.** Without any plugins enabled, the core Romanesco
    application can only perform two types of tasks: ``python`` and ``workflow`` modes.
    It's common for plugins to implement other task execution modes.
  * **Adding new data types or formats.** Plugins can make Romanesco aware of new
    data types and formats, and provide implementations for how to validate and
    convert to and from those formats.
  * **Adding new IO modes.** One of the primary functions of Romanesco is to fetch
    input data from heterogenous sources and expose it to tasks in a uniform way.
    Plugins can implement novel modes of fetching and pushing input and output
    data for a task.

Below is a list of the plugins that are shipped with the romanesco package. They
can be enabled via the configuration file (see :ref:`configuration`).

Docker
------

* **Plugin ID:** ``docker``
* **Description:** This plugin exposes a new task execution mode, ``docker``. These
  tasks pull a docker image and run a container using that image, with optional
  command line arguments. Docker tasks look like:

.. code-block :: none

    <DOCKER_TASK> ::= {
        "mode": "docker",
        "docker_image": <docker image name to run>
        (, "container_args": [<container arguments>])
        (, "entrypoint": <custom override for container entry point>)
        (, "inputs": [<TASK_INPUT> (, <TASK_INPUT>, ...)])
        (, "outputs": [<TASK_OUTPUT> (, <TASK_OUTPUT>, ...)])
    }

The optional ``container_args`` parameter is a list of arguments to pass to the
container. If an ``entrypoint`` argument is passed, it will override the built-in
``ENTRYPOINT`` directive of the image. Since it's often the case that task inputs
will need to passed to the container as arguments, a special syntax can be used
to declare that a command line argument should be expanded at runtime to the value
of an input: ::

    "container_args": ["$input{my_input_id}"]

It is not necessary for the entire argument to be a variable expansion; any part of
an argument can also be expanded, e.g.: ::

    "container_args": ["--some-parameter=$input{some_parameter_value}"]

The temporary directory for the romanesco task is mapped into the running container
under the directory ``/data``, so any files that were fetched into that temp directory
will be available inside the running container at that path.

Girder IO
---------

* **Plugin ID:** ``girder_io``
* **Description:** This plugin adds new fetch and push modes called ``girder``. The
  fetch mode for inputs supports downloading folders, items, or files from a Girder
  server. Inputs can be downloaded anonymously (if they are public) or using an
  authentication token. This data is always written to disk within the task's
  temporary directory, and is always a ``string/text`` format since the data itself
  is simply the path to the downloaded file or directory.

.. code-block :: none

    <GIRDER_INPUT> ::= {
        "mode": "girder",
        "id": <the _id value of the resource to download>,
        "name": <the name of the resource to download>,
        "host": <the hostname of the girder server>,
        "format": "text",
        "type": "string"
        (, "port": <the port of the girder server, default is 80 for http: and 443 for https:>)
        (, "api_root": <path to the girder REST API, default is "/api/v1")
        (, "scheme": <"http" or "https", default is "http">)
        (, "token": <girder token used for authentication>)
        (, "resource_type": <"file", "item", or "folder", default is "file">)
    }

The output mode also assumes data of format ``string/text`` that is a path to a file
in the filesystem. That file will then be uploaded under an existing folder (under a
new item with the same name as the file), or into an existing item.

.. code-block :: none

    <GIRDER_OUTPUT> ::= {
        "mode": "girder",
        "parent_id": <the _id value of the folder or item to upload into>,
        "name": <the name of the resource to download>,
        "host": <the hostname of the girder server>,
        "format": "text",
        "type": "string"
        (, "port": <the port of the girder server, default is 80 for http and 443 for https>)
        (, "api_root": <path to the girder REST API, default is "/api/v1")
        (, "scheme": <"http" or "https", default is "http">)
        (, "token": <girder token used for authentication>)
        (, "parent_type": <"folder" or "item", default is "folder">)
    }
R
-

* **Plugin ID:** ``r``
* **Description:** The R plugin enables the execution of R scripts as tasks via
  the ``r`` execution mode. It also exposes a new data type, ``r``, and several
  new data formats and converters for existing data types. Just like ``python`` mode,
  the R code to run is passed via the ``script`` field of the task specification.
  The ``r`` data type refers to objects compatible with the R runtime environment.
* **Converters added:**
    * ``r/object`` |ba| ``r/serialized``: Convert between in-memory R object and a serialized version.
    * ``table/csv`` |ba| ``table/r.dataframe``
    * ``tree/newick`` |ba| ``tree/r.apetree``
    * ``tree/nexus`` |ba| ``tree/r.apetree``
    * ``r/apetree`` |ra| ``tree/treestore``

* **Validators added:**
    * ``r/object``
    * ``r/serialized``
    * ``table/r.dataframe``
    * ``tree/r.apetree``

Spark
-----

* **Plugin ID:** ``spark``
* **Description:** Adds a new execution mode ``spark.python`` that allows tasks to
  run inside a pyspark environment with a
  `SparkContext <http://spark.apache.org/docs/latest/api/scala/index.html#org.apache.spark.SparkContext>`_
  variable automatically exposed. That is, each task will have a variable exposed
  in its python runtime called ``sc`` that is a valid SparkContext. This plugin exposes
  a new type, ``collection``, referring to something that can be represented by
  a Spark `RDD <http://spark.apache.org/docs/latest/api/scala/index.html#org.apache.spark.rdd.RDD>`_.
* **Converters added:**
    * ``collection/json`` |ba| ``collection/spark.rdd``: Convert between a JSON list and an RDD created
      from calling ``sc.parallelize`` on the list.

* **Validators added:**
    * ``collection/json``
    * ``collection/spark.rdd``

VTK
---

* **Plugin ID:** ``vtk``
* **Description:** This plugin exposes the ``geometry`` type and provides converters
  and validators for several types. This plugin requires that you have the VTK
  python package exposed in Romanesco's python environment.
* **Converters added:**
    * ``geometry/vtkpolydata`` |ba| ``geometry/vtkpolydata.serialized``
    * ``table/rows`` |ba| ``table/vtktable``
    * ``table/vtktable`` |ba| ``table/vtktable.serialized``
    * ``tree/nested`` |ba| ``tree/vtktree``
    * ``tree/vtktree`` |ra| ``tree/newick``
    * ``tree/vtktree`` |ba| ``tree/vtktree.serialized``
    * ``graph/networkx`` |ba| ``graph/vtkgraph``
    * ``graph/vtkgraph`` |ba| ``graph/vtkgraph.serialized``

* **Validators added:**
    * ``geometry/vtkpolydata``
    * ``geometry/vtkpolydata.serialized``
    * ``table/vtktable``
    * ``table/vtktable.serialized``
    * ``tree/vtktree``
    * ``tree/vtktree.serialized``
    * ``graph/vtkgraph``
    * ``graph/vtkgraph.serialized``


    .. |ra| unicode:: 8594 .. right arrow
    .. |ba| unicode:: 8596 .. bidirectional arrow
