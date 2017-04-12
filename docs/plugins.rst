.. _worker-plugins:

Application Plugins
=======

The Girder Worker application plugin system is used to extend the core functionality of
Girder Worker in a number of ways. Application plugins can execute any Python code when
they are loaded at runtime, but the most common augmentations they perform are:

  * **Adding new execution modes.** Without any application plugins enabled, the core
    Girder Worker application can only perform two types of tasks: ``python`` and
    ``workflow`` modes. It's common for application plugins to implement other task
    execution modes.
  * **Adding new data types or formats.** Application plugins can make Girder Worker
    aware of new data types and formats, and provide implementations for how to validate
    and convert to and from those formats.
  * **Adding new IO modes.** One of the primary functions of Girder Worker is to fetch
    input data from heterogenous sources and expose it to tasks in a uniform way.
    Application plugins can implement novel modes of fetching and pushing input and
    output data for a task.

Below is a list of the application plugins that are shipped with the girder_worker package.
They can be enabled via the configuration file (see :ref:`configuration`).

Docker
------

* **Plugin ID:** ``docker``
* **Description:** This plugin exposes a new task execution mode, ``docker``. These
  tasks pull a Docker image and run a container using that image, with optional
  command line arguments. Docker tasks look like:

.. code-block :: none

    <DOCKER_TASK> ::= {
        "mode": "docker",
        "docker_image": <Docker image name to run>
        (, "pull_image": <true (the default) or false>)
        (, "container_args": [<container arguments>])
        (, "docker_run_args": [<additional arguments to `docker run`>])
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

Some command line arguments represent boolean flag values, and they should either be
present or absent depending on a boolean input value. For example, perhaps your container
accepts a command line argument ``--verbose`` to switch to verbose output. To support this
as an input, you could use the following task input:

.. code-block:: json

    {
    "id": "verbose",
    "name": "Verbose output",
    "description": "Prints more information during processing.",
    "type": "boolean",
    "format": "boolean",
    "arg": "--verbose"
    }

Then, in your ``container_args`` list, you can use a special ``$flag{id}`` token to control
whether this argument (specified via the ``arg`` parameter) is included or omitted:

.. code-block:: none

    "container_args": [..., "$flag{verbose}", ...]

The temporary directory for the Girder Worker task is mapped into the running container
under the directory ``/mnt/girder_worker/data``, so any files that were fetched into that
temp directory will be available inside the running container at that path.

By default, the image you specify will be pulled using the ``docker pull`` command.
In some cases, you may not want to perform a pull, and instead want to rely on the
image already being present on the worker system. If so, set ``pull_image`` to false.

To ensure the execution context is the expected one, it is recommended to
specify the ``docker_image`` using the ``Image[@digest]`` format (e.g. ``debian@sha256:cbbf2f9a99b47fc460d422812b6a5adff7dfee951d8fa2e4a98caa0382cfbdbf``). This will prevent
``docker pull`` from systematically downloading the latest available image. In that case,
setting ``pull_image`` to false is less relevant since the image will be pulled only if it
is not already available.

If you want to pass additional command line options to ``docker run`` that should
come before the container name, pass them as a list via the ``"docker_run_args"``
key.

Outputs from Docker tasks
*************************

Docker tasks can have two types of outputs: streams (i.e. standard output and standard
error) and files written by the container. If you want the contents of standard output
or standard error to become a task output, use the special output IDs ``_stdout`` or
``_stderr``, as in the following example:

.. code-block :: none

    "task": {
        "mode": "docker",
        "outputs": [{
            "id": "_stdout",
            "type": "string",
            "format": "text"
        }],
        ...

If you want to have your container write files that will be treated as outputs,
write them into the ``/mnt/girder_worker/data`` directory inside the container, then declare them
in the task output specification with ``"target": "filepath"``. The following
example shows how to specify a file written to ``/mnt/girder_worker/data/my_image.png`` as a
task output:

.. code-block :: none

    "task": {
        "mode": "docker",
        "outputs": [{
            "id": "my_image.png",
            "target": "filepath",
            "type": "string",
            "format": "text"
        }],
        ...

You don't have to use the output ID to specify the path; you can instead pass a
``path`` field in the output spec:

.. code-block :: none

    "task": {
        "mode": "docker",
        "outputs": [{
            "id": "some_output",
            "target": "filepath",
            "type": "string",
            "format": "text",
            "path": "/mnt/girder_worker/data/some_subdirectory/my_image.png"
        }],
        ...

Paths that are specified as relative paths are assumed to be relative to ``/mnt/girder_worker/data``.
If you specify an absolute path, it must start with ``/mnt/girder_worker/data/``, otherwise an exception
will be thrown before the task is run. These conventions apply whether the path
is specified in the ``id`` or ``path`` field.

Management of Docker Containers and Images
******************************************

Docker images may be pulled when a task is run.  By default, these images are
never removed.  Docker containers are automatically removed when the task is
complete.

As an alternative, a 'garbage collection' process can be used instead.  It can
be enabled by modifying settings in the ``[docker]`` section of the config 
file, which can be done using the command:

.. code-block :: none

  girder-worker-config set docker gc True

When the ``gc`` config value is set to ``True``, containers are not removed 
when the task ends.  Instead, periodically, any images not associated with a
container will be removed, and then any stopped containers will be removed.
This will free disk space associated with the images, but may remove images
that are not directly related to Girder Worker.

When garbage collection is turned on, images can be excluded from the process
by setting ``exclude_images`` to a comma-separated list of image names.  For
instance:

.. code-block :: none

  girder-worker-config set docker exclude_images dsarchive/histomicstk,rabbitmq

Only containers that have been stopped longer than a certain time are removed.
This time defaults to an hour, and can be specified as any number of seconds
via the ``cache_timeout`` setting.


Girder IO
---------

* **Plugin ID:** ``girder_io``
* **Description:** This plugin adds new fetch and push modes called ``girder``. The
  fetch mode for inputs supports downloading folders, items, or files from a Girder
  server. Inputs can be downloaded anonymously (if they are public) or using an
  authentication token. The downloaded data is either written to disk and passed
  as a file, or read into memory, depending on whether the corresponding task
  input's ``target`` field is set to ``"filepath"`` or ``"memory"``. Likewise for
  uploads, the value of the output variable is interpreted as a path to a file to
  be uploaded if the task output ``target`` is set to ``filepath``. If it's set to
  ``memory``, the value of the output variable becomes the contents of the uploaded
  file. The URL to access the Girder API must be specified either as a full URL in
  the ``api_url`` field, or in parts via the ``host``, ``port``, ``api_root``, and
  ``scheme`` fields.

.. code-block :: none

    <GIRDER_INPUT> ::= {
        "mode": "girder",
        "id": <the _id value of the resource to download>,
        "name": <the name of the resource to download>,
        "format": "text",
        "type": "string"
        (, "api_url": <full URL to the API, can be used instead of scheme/host/port/api_root>)
        (, "host": <the hostname of the girder server. Required if no api_url is passed>)
        (, "port": <the port of the girder server, default is 80 for http: and 443 for https:>)
        (, "api_root": <path to the girder REST API, default is "/api/v1")
        (, "scheme": <"http" or "https", default is "http">)
        (, "token": <girder token used for authentication>)
        (, "resource_type": <"file", "item", or "folder", default is "file">)
        (, "fetch_parent": <whether to download the whole parent resource as well, default is false>)
    }

.. note :: For historical reasons, task inputs that do not specify a ``target`` field
   and are bound to a Girder input will default to having the data downloaded to
   a file (i.e. ``target="filepath"`` behavior). This is different from the normal
   default behavior for other IO modes, which is to download the data to an
   object in memory. For this reason, it is suggested that if your task input is going
   to support Girder IO mode, that you specify the ``target`` field explicitly
   on it rather than using the default.

The output mode also assumes data of format ``string/text`` that is a path to a file
in the filesystem. That file will then be uploaded under an existing folder (under a
new item with the same name as the file), or into an existing item.

.. code-block :: none

    <GIRDER_OUTPUT> ::= {
        "mode": "girder",
        "token": <girder token used for authentication>,
        "parent_id": <the _id value of the folder or item to upload into>,
        "format": "text",
        "type": "string"
        (, "name": <optionally override name of the file to upload>)
        (, "api_url": <full URL to the API, can be used instead of scheme/host/port/api_root>)
        (, "host": <the hostname of the girder server. Required if no api_url is passed>)
        (, "port": <the port of the girder server, default is 80 for http: and 443 for https:>)
        (, "api_root": <path to the girder REST API, default is "/api/v1")
        (, "scheme": <"http" or "https", default is "http">)
        (, "parent_type": <"folder" or "item", default is "folder">)
        (, "reference": <arbitrary reference string to pass to the server>)
    }

Cache Configuration
*******************

The Girder Client (used by the Girder IO plugin) supports caching of files
downloaded from Girder. These cache settings are exposed in the Girder Worker
configuration.  The following options are available:

  * ``diskcache_enabled`` (default=0): enable or disable diskcache for files
    downloaded with the girder client
  * ``diskcache_directory`` (default=girder_file_cache): directory to use for
    the diskcache
  * ``diskcache_eviction_policy`` (default=least-recently-used): eviction policy
    used when diskcache size limit is reached
  * ``diskcache_size_limit`` (default=1073741824): maximum size of the disk
    cache, 1GB default
  * ``diskcache_cull_limit`` (default=10): maximum number of items to cull when
    evicting items
  * ``diskcache_large_value_threshold`` (default=1024): cached values below this
    size are stored directly in the cache's sqlite db

R
-

* **Plugin ID:** ``r``
* **Description:** The R plugin enables the execution of R scripts as tasks via
  the ``r`` execution mode. It also exposes a new data type, ``r``, and several
  new data formats and converters for existing data types. Just like ``python`` mode,
  the R code to run is passed via the ``script`` field of the task specification.
  The ``r`` data type refers to objects compatible with the R runtime environment.
* **Converters added:**
    * ``r/object`` |ba| ``r/serialized``
    * ``table/csv`` |ba| ``table/r.dataframe``
    * ``tree/newick`` |ba| ``tree/r.apetree``
    * ``tree/nexus`` |ba| ``tree/r.apetree``
    * ``tree/r.apetree`` |ra| ``tree/treestore``

* **Validators added:**
    * ``r/object``: An in-memory R object.
    * ``r/serialized``: A serialized version of an R object created using R's ``serialize`` function.
    * ``table/r.dataframe``: An R data frame. If the first column contains unique values,
      these are set as the row names of the data frame.
    * ``tree/r.apetree``: A tree in the R package ``ape`` format.

Spark
-----

* **Plugin ID:** ``spark``
* **Description:** Adds a new execution mode ``spark.python`` that allows tasks to
  run inside a pyspark environment with a
  `SparkContext <http://spark.apache.org/docs/latest/api/scala/index.html#org.apache.spark.SparkContext>`_
  variable automatically exposed. That is, each task will have a variable exposed
  in its Python runtime called ``sc`` that is a valid SparkContext. This plugin exposes
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
  Python package exposed in Girder Worker's Python environment. The ``geometry`` type
  represents 3D geometry.
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
    * ``geometry/vtkpolydata``: A vtkPolyData_ object.
    * ``geometry/vtkpolydata.serialized``: A vtkPolyData serialized with vtkPolyDataWriter_.
    * ``table/vtktable``: A vtkTable_.
    * ``table/vtktable.serialized``: A vtkTable serialized with vtkTableWriter_.
    * ``tree/vtktree``: A vtkTree_.
    * ``tree/vtktree.serialized``: A vtkTree serialized with vtkTreeWriter_.
    * ``graph/vtkgraph``: A vtkGraph_.
    * ``graph/vtkgraph.serialized``: A vtkGraph serialized with vtkGraphWriter_.

.. note :: vtkGraphs lose their actual node values as they are represented by their index.
  In addition, nodes and edges are given all metadata attributes with defaults if they do not specify the metadatum themselves.
  This is noted further in :py:mod:`girder_worker.core.plugins.vtk.converters.graph.networkx_to_vtkgraph`

.. _vtkGraph: http://www.vtk.org/doc/nightly/html/classvtkGraph.html
.. _vtkGraphWriter: http://www.vtk.org/doc/nightly/html/classvtkGraphWriter.html
.. _vtkTree: http://www.vtk.org/doc/nightly/html/classvtkTree.html
.. _vtkTreeWriter: http://www.vtk.org/doc/nightly/html/classvtkTreeWriter.html
.. _vtkTable: http://www.vtk.org/doc/nightly/html/classvtkTable.html
.. _vtkTableWriter: http://www.vtk.org/doc/nightly/html/classvtkTableWriter.html
.. _vtkPolyData: http://www.vtk.org/doc/nightly/html/classvtkPolyData.html
.. _vtkPolyDataWriter: http://www.vtk.org/doc/nightly/html/classvtkPolyDataWriter.html
.. _vtkTree: http://www.vtk.org/doc/nightly/html/classvtkTree.html

.. |ra| unicode:: 8594 .. right arrow
.. |ba| unicode:: 8596 .. bidirectional arrow
