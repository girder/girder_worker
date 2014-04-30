import csv
import json
import glob
import os
import romanesco.uri

def csv_to_rows(input, *pargs, **kwargs):
    if csv.Sniffer().has_header('\n'.join(input[:2048].splitlines())):
        reader = csv.DictReader(input.splitlines(), *pargs, **kwargs)
        rows = [d for d in reader]
        fields = reader.fieldnames
    else:
        reader = csv.reader(input.splitlines(), *pargs, **kwargs)
        rows = [{"Column " + str(index + 1): value for index, value in enumerate(row)} for row in reader]
        fields = []
        if len(rows) > 0:
            fields = ["Column " + str(index + 1) for index in range(len(rows[0]))]

    output = {"fields": fields, "rows": rows}

    # Attempt numeric conversion
    for row in output["rows"]:
        for col in row:
            try:
                row[col] = int(row[col])
            except:
                try:
                    row[col] = float(row[col])
                except:
                    pass

    return output

def vtkrow_to_dict(attributes, i):
    row = {}
    for c in range(attributes.GetNumberOfArrays()):
        variant_value = attributes.GetAbstractArray(c).GetVariantValue(i)
        if variant_value.IsInt():
            value = variant_value.ToInt()
        elif variant_value.IsLong():
            value = variant_value.ToLong()
        elif variant_value.IsDouble() or variant_value.IsFloat():
            value = variant_value.ToDouble()
        else:
            value = variant_value.ToString()
        row[attributes.GetAbstractArray(c).GetName()] = value
    return row

def dict_to_vtkarrays(row, fields, attributes):
    import vtk
    for key in fields:
        value = row[key]
        if isinstance(value, (int, long, float)):
            arr = vtk.vtkDoubleArray()
        elif isinstance(value, str):
            arr = vtk.vtkStringArray()
        elif isinstance(value, unicode):
            arr = vtk.vtkUnicodeStringArray()
        else:
            arr = vtk.vtkStringArray()
        arr.SetName(key)
        attributes.AddArray(arr)    

def dict_to_vtkrow(row, attributes):
    for key in row:
        value = row[key]
        if not isinstance(value, (int, long, float, str, unicode)):
            value = str(value)
        found = False
        for i in range(attributes.GetNumberOfArrays()):
            arr = attributes.GetAbstractArray(i)
            if arr.GetName() == key:
                arr.InsertNextValue(value)
                found = True
                break
        if not found:
            raise Exception("[dict_to_vtkrow] Unexpected key: " + key)

converters = {}
validators = {}

def import_converters(search_paths):
    prevdir = os.getcwd()
    for path in search_paths:
        os.chdir(path)
        for filename in glob.glob(os.path.join(path, "*.json")):
            with open(filename) as f:
                analysis = json.load(f)

            if not "script" in analysis:
                analysis["script"] = romanesco.uri.get_uri(analysis["script_uri"])

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
    
    # print "digraph g {"
    # for analysis_type, analysis_type_values in converters.iteritems():
    #     for input_format, input_format_values in analysis_type_values.iteritems():
    #         for output_format in input_format_values:
    #             print '"' + analysis_type + ":" + input_format + '" -> "' + analysis_type + ":" + output_format + '"'
    # print "}"

    print "from,to"
    for analysis_type, analysis_type_values in converters.iteritems():
        for input_format, input_format_values in analysis_type_values.iteritems():
            for output_format in input_format_values:
                print analysis_type + ":" + input_format + "," + analysis_type + ":" + output_format

    max_steps = 3
    for i in range(max_steps):
        to_add = []
        for analysis_type, analysis_type_values in converters.iteritems():
            for input_format, input_format_values in analysis_type_values.iteritems():
                for output_format, converter in input_format_values.iteritems():
                    if output_format in analysis_type_values:
                        for next_output_format, next_converter in analysis_type_values[output_format].iteritems():
                            if input_format != next_output_format and next_output_format not in input_format_values:
                                to_add.append((analysis_type, input_format, next_output_format, converter + next_converter))
        for c in to_add:
            converters[c[0]][c[1]][c[2]] = c[3]

def import_default_converters():
    cur_path = os.path.dirname(os.path.realpath(__file__))
    import_converters([os.path.join(cur_path, t) for t in ["r", "table", "tree", "string", "number", "image", "boolean"]])

import_default_converters()
