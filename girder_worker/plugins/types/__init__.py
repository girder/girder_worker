from networkx import NetworkXNoPath

from girder_worker import utils
from girder_worker.core import events, io, run, set_job_status
from .format import conv_graph, converter_path, get_validator_analysis, Validator


def isvalid(type, binding, fetch=True, **kwargs):
    """
    Determine whether a data binding is of the appropriate type and format.

    :param type: The expected type specifier string of the binding.
    :param binding: A binding dict of the form
        ``{'format': format, 'data', data}``, where ``format`` is the format
        specifier string, and ``data`` is the raw data to test.
        The dict may also be of the form
        ``{'format': format, 'uri', uri}``, where ``uri`` is the location of
        the data (see :py:mod:`girder_worker.uri` for URI formats).
    :param fetch: Whether to do an initial data fetch before conversion
        (default ``True``).
    :returns: ``True`` if the binding matches the type and format,
        ``False`` otherwise.
    """
    kwargs = kwargs.copy()
    kwargs['auto_convert'] = False
    kwargs['validate'] = False

    analysis = get_validator_analysis(Validator(type, binding['format']))
    outputs = run(analysis, {'input': binding}, fetch=fetch, **kwargs)
    return outputs['output']['data']


def convert(type, input, output, fetch=True, status=None, **kwargs):
    """
    Convert data from one format to another.

    :param type: The type specifier string of the input data.
    :param input: A binding dict of the form
        ``{'format': format, 'data', data}``, where ``format`` is the format
        specifier string, and ``data`` is the raw data to convert.
        The dict may also be of the form
        ``{'format': format, 'uri', uri}``, where ``uri`` is the location of
        the data (see :py:mod:`girder_worker.uri` for URI formats).
    :param output: A binding of the form
        ``{'format': format}``, where ``format`` is the format
        specifier string to convert the data to.
        The binding may also be in the form
        ``{'format': format, 'uri', uri}``, where ``uri`` specifies
        where to place the converted data.
    :param fetch: Whether to do an initial data fetch before conversion
        (default ``True``).
    :returns: The output binding
        dict with an additional field ``'data'`` containing the converted data.
        If ``'uri'`` is present in the output binding, instead saves the data
        to the specified URI and
        returns the output binding unchanged.
    """
    kwargs = kwargs.copy()
    kwargs['auto_convert'] = False

    if fetch:
        input['data'] = io.fetch(input, **kwargs)

    if input['format'] == output['format']:
        data = input['data']
    else:
        data_descriptor = input
        try:
            conversion_path = converter_path(
                Validator(type, input['format']), Validator(type, output['format']))
        except NetworkXNoPath:
            raise Exception('No conversion path from %s/%s to %s/%s' % (
                type, input['format'], type, output['format']))

        # Run data_descriptor through each conversion in the path
        for conversion in conversion_path:
            result = run(
                conversion, {'input': data_descriptor}, status=status, **kwargs)
            data_descriptor = result['output']
        data = data_descriptor['data']

    if status == utils.JobStatus.CONVERTING_OUTPUT:
        job_mgr = kwargs.get('_job_manager')
        set_job_status(job_mgr, utils.JobStatus.PUSHING_OUTPUT)
    io.push(data, output, **kwargs)
    return output


def handle_input(e):
    task_input = e.info['task_input']
    input = e.info['input']
    name = e.info['name']
    kwargs = e.info['info']['kwargs']
    auto_convert = kwargs.get('auto_convert', True)
    validate = kwargs.get('validate', True)

    # Validate the input
    if validate and not isvalid(
            task_input['type'], input,
            **dict({'task_input': task_input, 'fetch': False}, **kwargs)):
        raise Exception(
            'Input %s (Python type %s) is not in the expected type (%s) and format (%s).' % (
                name, type(input['data']), task_input['type'], input['format']))

    # Convert data
    if auto_convert:
        try:
            converted = convert(
                task_input['type'], input, {'format': task_input['format']},
                status=utils.JobStatus.CONVERTING_INPUT,
                **dict({'task_input': task_input, 'fetch': False}, **kwargs))
        except Exception, e:
            raise Exception('%s: %s' % (name, str(e)))

        input['script_data'] = converted['data']
    elif not validate or input.get('format', task_input.get('format')) == task_input.get('format'):
        input['script_data'] = input['data']
    else:
        raise Exception(
            'Expected exact format match but \'%s != %s\'.' % (
                input['format'], task_input['format']))


def handle_output(e):
    task_output = e.info['task_output']
    outputs = e.info['outputs']
    name = e.info['name']
    kwargs = e.info['info']['kwargs']
    output = outputs[name]
    auto_convert = kwargs.get('auto_convert', True)
    validate = kwargs.get('validate', True)

    script_output = {
        'data': output['script_data'],
        'format': task_output.get('format')
    }
    if 'format' not in output:
        output['format'] = script_output['format']

    if validate and not isvalid(
            task_output['type'], script_output,
            **dict({'task_output': task_output}, **kwargs)):
        raise Exception(
            'Output %s (%s) is not in the expected type (%s) and format (%s).' % (
                name, type(script_output['data']), task_output['type'], output['format']))

    if auto_convert:
        outputs[name] = convert(
            task_output['type'], script_output, output, status=utils.JobStatus.CONVERTING_OUTPUT,
            **dict({'task_output': task_output}, **kwargs))
        e.prevent_default()  # convert handles the push for us
    elif validate and outputs[name]['format'] != task_output['format']:
        raise Exception(
            'Expected format match but %s != %s.' % (output['format'], task_output['format']))


def load(params):
    from girder_worker.app import app

    @app.task(name='girder_worker.convert')
    def _convert(*pargs, **kwargs):
        return convert(*pargs, **kwargs)

    @app.task(name='girder_worker.validators')
    def _validators(*pargs, **kwargs):
        type, format = pargs
        nodes = []

        for (node, data) in conv_graph.nodes(data=True):
            if type in (None, node.type) and format in (None, node.format):
                nodes.append({
                    'type': node.type,
                    'format': node.format,
                    'validator': data
                })

        return nodes

    events.bind('run.handle_input', params['name'], handle_input)
    events.bind('run.handle_output', params['name'], handle_output)
