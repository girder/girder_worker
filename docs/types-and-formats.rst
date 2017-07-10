.. _types-and-formats:

Types and formats
=================

In Girder Worker, analysis inputs and outputs may contain type and format annotations. These
annotations only have an effect if the ``types`` plugin is enabled on the worker,
and the specific behaviors of validation and conversion of data formats are controlled
by flags to the ``run`` task called ``validate`` and ``auto_convert`` respectively, which
default to being enabled if they are not explicitly passed.

A `type` in Girder Worker is a high-level description of a data structure useful for intuitive
workflows. It is not tied to a particular representation.
For example, the `table` type may be defined as a list of rows with ordered,
named column fields. This description does not specify any central representation
since the information may be stored in a variety of ways.
A type is specified by a string unique to your Girder Worker environment, such
as ``"table"`` for the table type.

An explicit representation of data is called a `format` in Girder Worker. A format
is a low-level description of data layout. For example, the table type may have
formats for CSV, database table, R data frame, or JSON. The format may be text,
serialized binary, or even in-memory data layouts. Just like types, a format is
specified by a string unique to your Girder Worker environment, such as ``"csv"``
for the CSV format. Formats under the same type should be convertible
between each other.

Notice that the above uses the phrases such as "may be defined" and "may have formats".
This is because at its core Girder Worker does not contain types or formats.
The :py:func:`girder_worker.run` function will attempt to match given input bindings
to analysis inputs, validating data and performing conversions as needed.
To make Girder Worker aware of certain types and formats, you must define validation and
conversion routines. These routines are themselves Girder Worker algorithms of a
particular form, loaded with
:py:func:`girder_worker.plugins.types.format.import_converters`. See that function's documentation
for how to define validators and converters.

The following are the types available in Girder Worker core. Application plugins may add their
own types and formats using the ``girder_worker.plugins.types.format.import_converters`` function. See
the :doc:`plugins` section for details on plugin-specific types and formats.


``"boolean"`` type
-----------------------
A true or false value. Formats:

:``"boolean"``: An in-memory Python ``bool``.

:``"json"``: A JSON string representing a single boolean (``"true"`` or ``"false"``).

``"integer"`` type
-----------------------
An integer. Formats:

:``"integer"``: An in-memory Python ``int``.

:``"json"``: A JSON string representing a single integer.

``"number"`` type
-----------------------
A numeric value (integer or real). Formats:

:``"number"``: An in-memory Python ``int`` or ``float``.

:``"json"``: A JSON string representing a single number.

``"string"`` type
-----------------------
A sequence of characters.

:``"text"``: A raw string of characters (``str`` in Python).

:``"json"``: A JSON string representing a single string.
    This is a quoted string with certain characters escaped.

``"integer_list"`` type
-----------------------
A list of integers. Formats:

:``"integer_list"``: An in-memory list of Python ``int``.

:``"json"``: A JSON string representing a list of integers.

``"number_list"`` type
-----------------------
A list of numbers (integer or real). Formats:

:``"number_list"``: An in-memory list of Python ``int`` or ``float``.

:``"json"``: A JSON string representing a list of numbers.

``"string_list"`` type
-----------------------
A list of strings. Formats:

:``"string_list"``: An in-memory list of Python ``str``.

:``"json"``: A JSON string representing a list of strings.

``"table"`` type
-----------------------
A list of rows with ordered, named column attributes. Formats:

:``"rows"``: A Python dictionary containing keys ``"fields"`` and ``"rows"``.
    ``"fields"`` is a list of column names that specifies column order.
    ``"rows"`` is a list of dictionaries of the form ``field: value``
    where ``field`` is the field name and ``value`` is the value
    of the field for that row. For example: ::

        {
            "fields": ["one", "two"],
            "rows": [{"one": 1, "two": 2}, {"one": 3, "two": 4}]
        }

:``"rows.json"``: The equivalent JSON representation of the ``"rows"`` format.

:``"objectlist"``: A Python list of dictionaries of the form ``field: value``
    where ``field`` is the field name and ``value`` is the value
    of the field for that row. For example: ::

        [{"one": 1, "two": 2}, {"one": 3, "two": 4}]

    This is identical to the ``"rows"`` field of the ``"rows"`` format.
    Note that this format does not preserve column ordering.

:``"objectlist.json"``: The equivalent JSON representation of the
    ``"objectlist"`` format.

:``"objectlist.bson"``: The equivalent BSON representation of the
    ``"objectlist"`` format. This is the format of MongoDB collections.

:``"csv"``: A string containing the contents of a comma-separated CSV file.
    The first line of the file is assumed to contain column headers.

:``"tsv"``: A string containing the contents of a tab-separated TSV file.
    Column headers are detected the same as for the ``"csv"`` format.


``"tree"`` type
-----------------------
A hierarchy of nodes with node and/or link attributes. Formats:

:``"nested"``: A nested Python dictionary representing the tree.
    All nodes may contain a ``"children"`` key containing a list
    of child nodes. Nodes may also contain ``"node_data"`` and ``"edge_data"``
    which are ``name: value`` dictionaries of node and edge attributes.
    The top-level (root node) dictionary contains ``"node_fields"`` and ``"edge_fields"``
    which are lists of node and edge attribute names to preserve ordering.
    The root should not contain ``"edge_data"`` since it does not have a parent edge.
    For example: ::

        {
            "edge_fields": ["weight"],
            "node_fields": ["node name", "node weight"],
            "node_data": {"node name": "", "node weight": 0.0},
            "children": [
                {
                    "node_data": {"node name": "", "node weight": 2.0},
                    "edge_data": {"weight": 2.0},
                    "children": [
                        {
                            "node_data": {"node name": "ahli", "node weight": 2.0},
                            "edge_data": {"weight": 0.0}
                        },
                        {
                            "node_data": {"node name": "allogus", "node weight": 3.0},
                            "edge_data": {"weight": 1.0}
                        }
                    ]
                },
                {
                    "node_data": {"node name": "rubribarbus", "node weight": 3.0},
                    "edge_data": {"weight": 3.0}
                }
            ]
        }

:``"nested.json"``: The equivalent JSON representation of the ``"nested"`` format.

:``"newick"``: A tree in Newick format.

:``"nexus"``: A tree in Nexus format.

:``"phyloxml"``: A phylogenetic tree in PhyloXML format.


``"graph"`` type
-----------------------
A collection of nodes and edges with optional attributes. Formats:

:``"networkx"``: An in-memory representation of a graph using an object of type nx.Graph_ (or any of its subclasses).

:``"networkx.json"``: A JSON representation of a NetworkX graph.

:``"clique.json"``: A JSON representation of a Clique_ graph.

:``"graphml"``: An XML String representing a valid GraphML_ representation.

:``"adjacencylist"``: A string representing a very simple `adjacency list`_ which does not preserve node or edge attributes.

.. _nx.Graph: https://networkx.github.io/documentation/latest/reference/classes.graph.html
.. _Clique: https://github.com/Kitware/clique
.. _GraphML: https://networkx.github.io/documentation/latest/reference/readwrite.graphml.html
.. _`adjacency list`: https://networkx.github.io/documentation/latest/reference/readwrite.adjlist.html#format

``"image"`` type
-----------------------
A 2D matrix of uniformly-typed numbers. Formats:

:``"png"``: An image in PNG format.

:``"png.base64"``: A Base-64 encoded PNG image.

:``"pil"``: An image as a ``PIL.Image`` from the Python Imaging Library.
