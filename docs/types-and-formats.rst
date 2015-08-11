Types and formats
=================

In Romanesco, every analysis input and output is typed. A `type` in Romanesco is a
high-level description of a data structure useful for intuitive workflows.
It is not tied to a particular representation.
For example, the `table` type may be defined as a list of rows with ordered,
named column fields. This description does not specify any central representation
since the information may be stored in a variety of ways.
A type is specified by a string unique to your Romanesco environment, such
as ``"table"`` for the table type.

An explicit representation of data is called a `format` in Romanesco. A format
is a low-level description of data layout. For example, the table type may have
formats for CSV, database table, R data frame, or JSON. The format may be text,
serialized binary, or even in-memory data layouts. Just like types, a format is
specified by a string unique to your Romanesco environment, such as ``"csv"``
for the CSV format. Formats under the same type should be convertable
between each other.

Notice that the above uses the phrases such as "may be defined" and "may have formats".
This is because at its core Romanesco does not contain types or formats.
The :py:func:`romanesco.run` function will attempt to match given input bindings
to analysis inputs, validating data and performing conversions as needed.
To make Romanesco aware of certain types and formats, you must define validation and
conversion routines. These routines are themselves Romanesco algorithms of a
particular form, loaded with
:py:func:`romanesco.format.import_converters`. See that function's documentation
for how to define validators and converters.

The following are the types available to the Romanesco system by default.
Add or remove files and directories in the ``romanesco/format`` directory
to customize the available formats.

``"boolean"`` type
-----------------------
A truthy or falsy value. Formats:

:``"boolean"``: An in-memory Python ``bool``.

:``"json"``: A JSON string representing a single boolean (``"true"`` or ``"false"``).

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
    Column headers will be reasonably detected if present, otherwise
    columns will be named ``"Column 1"``, ``Column 2"``, etc.
    See `has_header`_ for details on header detection.

:``"tsv"``: A string containing the contents of a tab-separated TSV file.
    Column headers are detected the same as for the ``"csv"`` format.

:``"r.dataframe"``: An R data frame. If the first column contains unique values,
    these are set as the row names of the data frame.

:``"vtktable"``: A vtkTable_.

:``"vtktable.serialized"``: A vtkTable serialized with vtkTableWriter_.

.. _`has_header`: https://docs.python.org/3.1/library/csv.html#csv.Sniffer.has_header
.. _vtkTable: http://www.vtk.org/doc/nightly/html/classvtkTable.html
.. _vtkTableWriter: http://www.vtk.org/doc/nightly/html/classvtkTableWriter.html

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

:``"vtktree"``: A vtkTree_.

:``"vtktree.serialized"``: A vtkTree serialized with vtkTreeWriter_.

:``"r.apetree"``: A tree in the R package ``"ape"`` format.

:``"newick"``: A tree in Newick format.

:``"nexus"``: A tree in Nexus format.

:``"phyloxml"``: A phylogenetic tree in PhyloXML format.

.. _vtkTree: http://www.vtk.org/doc/nightly/html/classvtkTree.html
.. _vtkTreeWriter: http://www.vtk.org/doc/nightly/html/classvtkTreeWriter.html

``"graph"`` type
-----------------------
A collection of nodes and edges with optional attributes. Formats:

:``"networkx"``: A representation of a graph using an object of type nx.Graph_ (or any of its subclasses).

:``"networkx.json"``: A JSON representation of a NetworkX graph.

:``"graphml"``: An XML String representing a valid GraphML_ representation.

:``"adjacencylist"``: A string representing a very simple `adjacency list`_ which does not preserve node or edge attributes.

:``"vtkgraph"``: A vtkGraph_.

:``"vtkgraph.serialized"``: A vtkGraph serialized with vtkGraphWriter_.

.. _nx.Graph: https://networkx.github.io/documentation/latest/reference/classes.graph.html
.. _GraphML: https://networkx.github.io/documentation/latest/reference/readwrite.graphml.html
.. _`adjacency list`: https://networkx.github.io/documentation/latest/reference/readwrite.adjlist.html#format
.. _vtkGraph: http://www.vtk.org/doc/nightly/html/classvtkGraph.html
.. _vtkGraphWriter: http://www.vtk.org/doc/nightly/html/classvtkGraphWriter.html

``"image"`` type
-----------------------
A 2D matrix of uniformly-typed numbers. Formats:

:``"png"``: An image in PNG format.

:``"png.base64"``: A Base-64 encoded PNG image.

:``"pil"``: An image as a ``PIL.Image`` from the Python Imaging Library.

``"r"`` type
-----------------------
An arbitrary R object.

:``"object"``: An in-memory R object.

:``"serialized"``: An R object serialized with R's ``serialize`` function.

`"geometry"` type
-----------------------
3D geometry. Formats:

:``"vtkpolydata"``: A vtkPolyData_ object.

:``"vtkpolydata.serialized"``: A vtkPolyData serialized with vtkPolyDataWriter_.

.. _vtkPolyData: http://www.vtk.org/doc/nightly/html/classvtkPolyData.html
.. _vtkPolyDataWriter: http://www.vtk.org/doc/nightly/html/classvtkPolyDataWriter.html
