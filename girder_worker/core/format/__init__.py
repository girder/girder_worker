import csv
import json
import glob
import os
import math
from girder_worker.core.io import fetch
import networkx as nx
from collections import namedtuple
from networkx.algorithms.shortest_paths.generic import all_shortest_paths
from networkx.algorithms.shortest_paths.unweighted import (
    single_source_shortest_path
)


conv_graph = nx.DiGraph()


class Validator(namedtuple('Validator', ['type', 'format'])):
    """Validator

    .. py:attribute:: type

        The validator type, like ``string``.

    .. py:attribute:: format

        The validator format, like ``text``.
    """

    def is_valid(self):
        """Return whether the type/format combination is valid.

        If format is None, checks for the presence of any valid type/format with
        the specified type.

        :returns: ``True`` if ``type`` and ``format`` are a valid, loaded
            type/format pair.
        """
        if self.format is None:
            return self.type in set(v.type for v in conv_graph.nodes())

        return self in conv_graph.nodes()


def get_csv_reader(input):

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
    return csv.DictReader(input.splitlines(), dialect=dialect)


def csv_to_rows(input):
    reader = get_csv_reader(input)
    rows = [d for d in reader]
    fields = reader.fieldnames

    output = {'fields': fields, 'rows': rows}

    # Attempt numeric conversion
    for row in output['rows']:
        for col in row:
            try:
                row[col] = int(row[col])
            except Exception:
                try:
                    orig = row[col]
                    row[col] = float(row[col])

                    # Disallow NaN, Inf, -Inf since this does not
                    # pass through JSON converters cleanly
                    if math.isnan(row[col]) or math.isinf(row[col]):
                        row[col] = orig
                except Exception:
                    pass

    return output


def converter_path(source, target):
    """Gives the shortest path that should be taken to go from a source
    type/format to a target type/format.

    Throws a ``NetworkXNoPath`` exception if it can not find a path.

    :param source: Validator tuple indicating the type/format being converted
        `from`.
    :param target: ``Validator`` tuple indicating the type/format being
        converted `to`.
    :returns: An ordered list of the analyses that need to be run to convert
        from ``source`` to ``target``.
    """
    # These are to ensure an exception gets thrown if source/target don't exist
    get_validator_analysis(source)
    get_validator_analysis(target)

    # We sort and pick the first of the shortest paths just to produce a stable
    # conversion path. This is stable in regards to which plugins are loaded at
    # the time.
    paths = all_shortest_paths(conv_graph, source, target)
    path = sorted(paths)[0]
    path = zip(path[:-1], path[1:])

    return [conv_graph.edge[u][v] for (u, v) in path]


def has_converter(source, target=Validator(type=None, format=None)):
    """Determines if any converters exist from a given type, and optionally format.

    Underneath, this just traverses the edges until it finds one which matches
    the arguments.

    :param source: ``Validator`` tuple indicating the type/format being
        converted `from`.
    :param target: ``Validator`` tuple indicating the type/format being
        converted `to`.
    :returns: ``True`` if it can converter from ``source`` to ``target``,
        ``False`` otherwise.
    """
    sources = []

    for node in conv_graph.nodes():
        if ((source.type is None) or (source.type == node.type)) and \
           ((source.format is None) or (source.format == node.format)):
            sources.append(node)

    for u in sources:
        reachable = single_source_shortest_path(conv_graph, u)
        del reachable[u]  # Ignore path to self, since there are no self loops

        for v in reachable:
            if ((target.type is None) or (target.type == v.type)) and \
               ((target.format is None) or (target.format == v.format)):
                return True

    return False


def get_validator_analysis(validator):
    """Gets a validator's analysis from the conversion graph.

    >>> analysis = get_validator_analysis(Validator('string', 'text'))

    Returns an analysis dictionary

    >>> type(analysis) == dict
    True

    Which contains an inputs key

    >>> 'inputs' in analysis
    True

    If the validator doesn't exist, an exception will be raised

    >>> get_validator_analysis(Validator('foo', 'bar'))
    Traceback (most recent call last):
    ...
    Exception: No such validator foo/bar

    :param validator: A ``Validator`` namedtuple
    :returns: A dictionary containing the runnable analysis.
    """
    try:
        return conv_graph.node[validator]
    except KeyError:
        raise Exception(
            'No such validator %s/%s' % (validator.type, validator.format))


def import_converters(search_paths):
    """
    Import converters and validators from the specified search paths.
    These functions are loaded into ``girder_worker.format.conv_graph`` with
    nodes representing validators, and directed edges representing
    converters.

    Any files in a search path matching ``validate_*.json`` are loaded
    as validators. Validators should be fast (ideally O(1)) algorithms
    for determining if data is of the specified format. These are algorithms
    that have a single input named ``"input"`` and a single output named
    ``"output"``. The input has the type and format to be checked.
    The output must have type and format ``"boolean"``. The script performs
    the validation and sets the output variable to either true or false.

    Any ``*_to_*.json`` files are imported as converters.
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

            if 'script' not in analysis:
                analysis['script'] = fetch({
                    'mode': analysis.get('script_fetch_mode', 'auto'),
                    'url': analysis['script_uri']
                })

        return analysis

    prevdir = os.getcwd()
    for path in search_paths:
        os.chdir(path)
        validator_files = set(glob.glob(os.path.join(path, 'validate_*.json')))
        converter_files = set(glob.glob(os.path.join(
            path, '*_to_*.json'))) - validator_files

        for filename in validator_files:
            analysis = get_analysis(filename)

            # Validators only contain 1 input and output, so the type/format of
            # it can be gleaned from the first input.
            conv_graph.add_node(Validator(analysis['inputs'][0]['type'],
                                          analysis['inputs'][0]['format']),
                                analysis)

        for filename in converter_files:
            analysis = get_analysis(filename)
            in_type = analysis['inputs'][0]['type']
            in_format = analysis['inputs'][0]['format']
            out_format = analysis['outputs'][0]['format']

            conv_graph.add_edge(Validator(in_type, in_format),
                                Validator(in_type, out_format),
                                attr_dict=analysis)

    os.chdir(prevdir)


def print_conversion_graph():
    """
    Print a graph of supported conversion paths in DOT format to standard
    output.
    """

    print 'digraph g {'

    for node in conv_graph.nodes():
        paths = single_source_shortest_path(conv_graph, node)
        reachable_conversions = [p for p in paths.keys() if p != node]

        for dest in reachable_conversions:
            print '"%s:%s" -> "%s:%s"' % (node[0], node[1], dest[0], dest[1])

    print '}'


def print_conversion_table():
    """
    Print a table of supported conversion paths in CSV format with ``'from'``
    and ``'to'`` columns to standard output.
    """

    print 'from,to'

    for node in conv_graph.nodes():
        paths = single_source_shortest_path(conv_graph, node)
        reachable_conversions = [p for p in paths.keys() if p != node]

        for dest in reachable_conversions:
            print '%s:%s,%s:%s' % (node[0], node[1], dest[0], dest[1])


def import_default_converters():
    """
    Import converters from the default search paths. This is called when the
    :py:mod:`girder_worker.format` module is first loaded.
    """

    cur_path = os.path.dirname(os.path.realpath(__file__))
    import_converters([os.path.join(cur_path, t) for t in [
        'boolean',
        'directory',
        'graph',
        'image',
        'integer',
        'integer_list',
        'netcdf',
        'number',
        'number_list',
        'python',
        'string',
        'string_list',
        'table',
        'tree']])


import_default_converters()
