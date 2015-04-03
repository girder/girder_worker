import csv
import json
import glob
import os
import math
import romanesco.io
from StringIO import StringIO


def csv_to_rows(input):

    # csv package does not support unicode
    input = str(input)

    # Special case: detect single-column files.
    # This check assumes that our only valid delimiters are commas and tabs.
    firstLine = input.split('\n')[0]
    if not ('\t' in firstLine or ',' in firstLine):
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


def vtkrow_to_dict(attributes, i):
    row = {}
    for c in range(attributes.GetNumberOfArrays()):
        arr = attributes.GetAbstractArray(c)
        values = []
        comp = arr.GetNumberOfComponents()
        for c in range(comp):
            variant_value = arr.GetVariantValue(i*comp + c)
            if variant_value.IsInt():
                value = variant_value.ToInt()
            elif variant_value.IsLong():
                value = variant_value.ToLong()
            elif variant_value.IsDouble() or variant_value.IsFloat():
                value = variant_value.ToDouble()
            else:
                value = variant_value.ToString()
            values.append(value)
        row[arr.GetName()] = values[0] if len(values) == 1 else values
    return row


def dict_to_vtkarrays(row, fields, attributes):
    import vtk
    for key in fields:
        value = row[key]
        comp = 1
        if isinstance(value, list):
            comp = len(value)
            value = value[0]
        if isinstance(value, (int, long, float)):
            arr = vtk.vtkDoubleArray()
        elif isinstance(value, str):
            arr = vtk.vtkStringArray()
        elif isinstance(value, unicode):
            arr = vtk.vtkUnicodeStringArray()
        else:
            arr = vtk.vtkStringArray()
        arr.SetName(key)
        arr.SetNumberOfComponents(comp)
        attributes.AddArray(arr)


def dict_to_vtkrow(row, attributes):
    for key in row:
        value = row[key]
        if not isinstance(value, (list, int, long, float, str, unicode)):
            value = str(value)
        found = False
        for i in range(attributes.GetNumberOfArrays()):
            arr = attributes.GetAbstractArray(i)
            if arr.GetName() == key:
                if isinstance(value, list):
                    for v in value:
                        arr.InsertNextValue(v)
                else:
                    arr.InsertNextValue(value)
                found = True
                break
        if not found:
            raise Exception("[dict_to_vtkrow] Unexpected key: " + key)

converters = {}
validators = {}


def import_converters(search_paths):
    """
    Import converters and validators from the specified search paths.
    These functions are loaded into the dictionaries
    ``romanesco.format.converters`` and ``romanesco.format.validators``
    and are made available to :py:func:`romanesco.convert`
    and :py:func:`romanesco.isvalid`.

    Any files in a search path matching ``validate_*.json`` are loaded
    as validators. Validators should be fast (ideally O(1)) algorithms
    for determining if data is of the specified format. These are algorithms
    that have a single input named ``"input"`` and a single output named
    ``"output"``. The input has the type and format to be checked.
    The output must have type and format ``"boolean"``. The script performs
    the validation and sets the output variable to either true or false.

    Any other ``.json`` files are imported as convertes.
    A converter is simply an analysis with one input named ``"input"`` and one
    output named ``"output"``. The input and output should have matching
    type but should be of different formats.

    :param search_paths: A list of search paths relative to the current
        working directory.
    """
    prevdir = os.getcwd()
    for path in search_paths:
        os.chdir(path)
        for filename in glob.glob(os.path.join(path, "*.json")):
            with open(filename) as f:
                analysis = json.load(f)

            if "script" not in analysis:
                analysis["script"] = romanesco.io.fetch({
                    "mode": analysis.get("script_fetch_mode", "auto"),
                    "url": analysis["script_uri"]
                })

            if os.path.basename(filename).startswith("validate_"):

                # This is a validator
                in_type = analysis["inputs"][0]["type"]
                in_format = analysis["inputs"][0]["format"]
                if in_type not in validators:
                    validators[in_type] = {}
                validators[in_type][in_format] = analysis

            else:

                # This is a converter
                in_type = analysis["inputs"][0]["type"]
                in_format = analysis["inputs"][0]["format"]
                out_format = analysis["outputs"][0]["format"]
                if in_type not in converters:
                    converters[in_type] = {}
                analysis_type = converters[in_type]
                if in_format not in analysis_type:
                    analysis_type[in_format] = {}
                input_format = analysis_type[in_format]
                if out_format not in input_format:
                    input_format[out_format] = {}
                input_format[out_format] = [analysis]

    os.chdir(prevdir)

    max_steps = 3
    for i in range(max_steps):
        to_add = []
        for analysis_type, analysis_type_values in converters.iteritems():
            for input_format, input_format_values in \
                    analysis_type_values.iteritems():
                for output_format, converter in \
                        input_format_values.iteritems():
                    if output_format in analysis_type_values:
                        output_formats = analysis_type_values[output_format]
                        for next_output_format, next_converter in \
                                output_formats.iteritems():
                            if input_format != next_output_format and \
                                    next_output_format not in \
                                    input_format_values:
                                to_add.append((analysis_type, input_format,
                                               next_output_format,
                                               converter + next_converter))
        for c in to_add:
            converters[c[0]][c[1]][c[2]] = c[3]


def print_conversion_graph():
    """
    Print a graph of supported conversion paths in DOT format to standard
    output.
    """

    print "digraph g {"
    for analysis_type, analysis_type_values in converters.iteritems():
        for input_format, input_format_values in \
                analysis_type_values.iteritems():
            for output_format in input_format_values:
                print '"' + analysis_type + ":" + input_format + '" -> "' \
                    + analysis_type + ":" + output_format + '"'
    print "}"


def print_conversion_table():
    """
    Print a table of supported conversion paths in CSV format with ``"from"``
    and ``"to"`` columns to standard output.
    """

    print "from,to"
    for analysis_type, analysis_type_values in converters.iteritems():
        for input_format, input_format_values in \
                analysis_type_values.iteritems():
            for output_format in input_format_values:
                print analysis_type + ":" + input_format + "," \
                    + analysis_type + ":" + output_format


def import_default_converters():
    """
    Import converters from the default search paths. This is called when the
    :py:mod:`romanesco.format` module is first loaded.
    """

    cur_path = os.path.dirname(os.path.realpath(__file__))
    import_converters([os.path.join(cur_path, t) for t in [
        "r", "table", "tree",
        "string", "number", "image",
        "boolean", "geometry"]])

import_default_converters()
