import csv
import json
import glob
import os
import math
import romanesco.io
import networkx as nx
from collections import namedtuple
from networkx.algorithms.shortest_paths.generic import shortest_path
from networkx.algorithms.shortest_paths.unweighted import single_source_shortest_path


Validator = namedtuple('Validator', ['type', 'format'])
conv_graph = nx.DiGraph()


def csv_to_rows(input):

    # csv package does not support unicode
    input = str(input)

    # Special case: detect single-column files.
    # This check assumes that our only valid delimiters are commas and tabs.
    firstLine = input.split('\n')[0]
    if not ('\t' in firstLine or ',' in firstLine) \
            or len(input.splitlines()) == 1:
        dialect = 'excel'

    else:
        # Take a data sample to determine dialect, but
        # don't include incomplete last line
        sample = ''
        sampleSize = 0
        while len(sample) == 0:
            sampleSize += 5000
            sample = '\n'.join(input[:sampleSize].splitlines()[:-1])
        dialect = csv.Sniffer().sniff(sample)
        dialect.skipinitialspace = True

    reader = csv.DictReader(input.splitlines(), dialect=dialect)
    rows = [d for d in reader]
    fields = reader.fieldnames

    output = {"fields": fields, "rows": rows}

    # Attempt numeric conversion
    for row in output["rows"]:
        for col in row:
            try:
                row[col] = int(row[col])
            except:
                try:
                    orig = row[col]
                    row[col] = float(row[col])

                    # Disallow NaN, Inf, -Inf since this does not
                    # pass through JSON converters cleanly
                    if math.isnan(row[col]) or math.isinf(row[col]):
                        row[col] = orig
                except:
                    pass

    return output


def converter_path(source, target):
    """Gives the shortest path that should be taken to go from a source
    type/format to a target type/format.

    Throws a NetworkXNoPath exception if it can not find a path.

    Returns a list of edges in the order they should be traversed.
    """
    # These are to ensure an exception gets thrown if source/target don't exist
    get_validator(source)
    get_validator(target)

    path = shortest_path(conv_graph, source, target)
    path = zip(path[:-1], path[1:])

    return [get_edge(u, v)[2] for (u, v) in path]


def has_converter(source, target=Validator(type=None, format=None)):
    """Determines if any converters exist from a given type, and possibly format.

    Further specificity can determine if a converter exists from a given type/format, to
    any other type/format.

    Underneath, this just traverses the edges until it finds one which matches the
    arguments.
    """
    for (u, v) in conv_graph.edges():
        if source.type and source.type != u.type:
            continue

        if source.format and source.format != u.format:
            continue

        if target.type and target.type != v.type:
            continue

        if target.format and target.format != v.format:
            continue

        return True

    return False


def get_edge(u, v):
    for edge in conv_graph.edges([u], data=True):
        if edge[1] == v:
            return edge

    return None


def get_validator(validator):
    """Gets a validator node from the conversion graph by its type and format.

    >>> validator = get_validator(Validator('string', 'text'))

    Returns a tuple containing 2 elements
    >>> len(validator)
    2

    First is the Validator namedtuple
    >>> validator[0]
    Validator(type=u'string', format=u'text')

    and second is the validator itself
    >>> validator[1].keys()
    ['validator', 'type', 'format']

    If the validator doesn't exist, an exception will be raised
    >>> get_validator(Validator('foo', 'bar'))
    Traceback (most recent call last):
       ...
    Exception: No such validator foo/bar
    """
    for (node, data) in conv_graph.nodes(data=True):
        if node == validator:
            return (node, data)

    raise Exception('No such validator %s/%s' % (validator.type, validator.format))


def import_converters(search_paths):
    """
    Import converters and validators from the specified search paths.
    These functions are loaded into ``romanesco.format.conv_graph`` with
    validators representing nodes, and converters representing directed
    edges.

    Any files in a search path matching ``validate_*.json`` are loaded
    as validators. Validators should be fast (ideally O(1)) algorithms
    for determining if data is of the specified format. These are algorithms
    that have a single input named ``"input"`` and a single output named
    ``"output"``. The input has the type and format to be checked.
    The output must have type and format ``"boolean"``. The script performs
    the validation and sets the output variable to either true or false.

    Any other ``.json`` files are imported as converters.
    A converter is simply an analysis with one input named ``"input"`` and one
    output named ``"output"``. The input and output should have matching
    type but should be of different formats.

    :param search_paths: A list of search paths relative to the current
        working directory. Passing a single path as a string also works.
    :type search_paths: str or list of str
    """
    if not isinstance(search_paths, (list, tuple)):
        search_paths = [search_paths]

    def get_analysis(filename):
        with open(filename) as f:
            analysis = json.load(f)

            if "script" not in analysis:
                analysis["script"] = romanesco.io.fetch({
                    "mode": analysis.get("script_fetch_mode", "auto"),
                    "url": analysis["script_uri"]
                })

        return analysis

    prevdir = os.getcwd()
    for path in search_paths:
        os.chdir(path)
        validator_files = set(glob.glob(os.path.join(path, "validate_*.json")))
        converter_files = set(glob.glob(os.path.join(path, "*.json"))) - validator_files

        for filename in validator_files:
            analysis = get_analysis(filename)

            in_type = analysis["inputs"][0]["type"]
            in_format = analysis["inputs"][0]["format"]

            conv_graph.add_node(Validator(in_type, in_format), {
                "type": analysis["inputs"][0]["type"],
                "format": analysis["inputs"][0]["format"],
                "validator": analysis
            })

        for filename in converter_files:
            analysis = get_analysis(filename)

            in_type = analysis["inputs"][0]["type"]
            in_format = analysis["inputs"][0]["format"]
            out_format = analysis["outputs"][0]["format"]

            conv_graph.add_edge(get_validator(Validator(in_type, in_format))[0],
                                get_validator(Validator(in_type, out_format))[0],
                                analysis)

    os.chdir(prevdir)


def print_conversion_graph():
    """
    Print a graph of supported conversion paths in DOT format to standard
    output.
    """

    print "digraph g {"

    for node in conv_graph.nodes():
        paths = single_source_shortest_path(conv_graph, node)
        reachable_conversions = [p for p in paths.keys() if p != node]

        for dest in reachable_conversions:
            print '"%s:%s" -> "%s:%s"' % (node[0], node[1], dest[0], dest[1])

    print "}"


def print_conversion_table():
    """
    Print a table of supported conversion paths in CSV format with ``"from"``
    and ``"to"`` columns to standard output.
    """

    print "from,to"

    for node in conv_graph.nodes():
        paths = single_source_shortest_path(conv_graph, node)
        reachable_conversions = [p for p in paths.keys() if p != node]

        for dest in reachable_conversions:
            print '%s:%s,%s:%s' % (node[0], node[1], dest[0], dest[1])


def import_default_converters():
    """
    Import converters from the default search paths. This is called when the
    :py:mod:`romanesco.format` module is first loaded.
    """

    cur_path = os.path.dirname(os.path.realpath(__file__))
    import_converters([os.path.join(cur_path, t) for t in [
        "table", "tree", "string", "number", "image", "directory", "boolean",
        "netcdf", "python", "graph"]])

import_default_converters()
