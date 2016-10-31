import os


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
            raise Exception('[dict_to_vtkrow] Unexpected key: ' + key)


def load(params):
    from girder_worker.core import format

    converters_dir = os.path.join(params['plugin_dir'], 'converters')
    format.import_converters([
        os.path.join(converters_dir, 'geometry'),
        os.path.join(converters_dir, 'graph'),
        os.path.join(converters_dir, 'table'),
        os.path.join(converters_dir, 'tree')
    ])
