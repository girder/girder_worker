import json
import glob
import os
import cardoon.uri

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

def dict_to_vtkarrays(row, attributes):
    import vtk
    for key in row:
        value = row[key]
        if isinstance(value, int):
            arr = vtk.vtkIntArray()
        elif isinstance(value, long):
            arr = vtk.vtkLongArray()
        elif isinstance(value, float):
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

def import_converters(search_paths):
    prevdir = os.getcwd()
    for path in search_paths:
        os.chdir(path)
        for filename in glob.glob(os.path.join(path, "*.json")):
            with open(filename) as f:
                analysis = json.load(f)
            if not "script" in analysis:
                analysis["script"] = cardoon.uri.get_uri(analysis["script_uri"])
            if analysis["inputs"][0]["type"] not in converters:
                converters[analysis["inputs"][0]["type"]] = {}
            analysis_type = converters[analysis["inputs"][0]["type"]]
            if analysis["inputs"][0]["format"] not in analysis_type:
                analysis_type[analysis["inputs"][0]["format"]] = {}
            input_format = analysis_type[analysis["inputs"][0]["format"]]
            if analysis["outputs"][0]["format"] not in input_format:
                input_format[analysis["outputs"][0]["format"]] = {}
            input_format[analysis["outputs"][0]["format"]] = [analysis]
    os.chdir(prevdir)
    
    # print "digraph g {"
    # for analysis_type, analysis_type_values in converters.iteritems():
    #     for input_format, input_format_values in analysis_type_values.iteritems():
    #         for output_format in input_format_values:
    #             print '"' + input_format + '" -> "' + output_format + '"'
    # print "}"

    max_steps = 3
    for i in range(max_steps):
        to_add = []
        for analysis_type, analysis_type_values in converters.iteritems():
            for input_format, input_format_values in analysis_type_values.iteritems():
                for output_format, converter in input_format_values.iteritems():
                    for next_output_format, next_converter in analysis_type_values[output_format].iteritems():
                        if input_format != next_output_format and next_output_format not in input_format_values:
                            to_add.append((analysis_type, input_format, next_output_format, converter + next_converter))
        for c in to_add:
            converters[c[0]][c[1]][c[2]] = c[3]

def import_default_converters():
    cur_path = os.path.dirname(os.path.realpath(__file__))
    import_converters([
        os.path.join(cur_path, "table"),
        os.path.join(cur_path, "tree"),
        os.path.join(cur_path, "string")
        ])

def convert(data, input_type, input_format, output_format):
    import cardoon
    if input_format == output_format:
        return data
    converter_path = converters[input_type][input_format][output_format]
    data_descriptor = {"data": data, "format": input_format}
    for c in converter_path:
        output = cardoon.run(c, {"input": data_descriptor}, auto_convert=False)
        data_descriptor = output["output"]
    return data_descriptor["data"]

import_default_converters()
