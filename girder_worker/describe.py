import six

from inspect import getdoc
try:
    from inspect import signature
except ImportError:
    from funcsigs import signature


class MissingDescriptionException(Exception):
    pass


class MissingInputException(Exception):
    pass


def get_description_attribute(func):
    description = getattr(func, '_girder_description', None)
    if description is None:
        raise MissingDescriptionException('Task is missing description decorators')
    return description


def argument(name, type, *args, **kwargs):
    """Describe an argument to a task."""

    if not isinstance(name, six.string_types):
        raise TypeError('Expected argument name to be a string')

    if callable(type):
        type = type(name, *args, **kwargs)

    def argument_wrapper(func):
        func._girder_description = getattr(func, '_girder_description', {})
        args = func._girder_description.setdefault('arguments', [])
        sig = signature(func)

        if name not in sig.parameters:
            raise ValueError('Invalid argument name "%s"' % name)

        type.set_parameter(sig.parameters[name], signature=sig)
        args.insert(0, type)
        return func

    return argument_wrapper


def describe_task(task):
    func = task.run
    description = get_description_attribute(func)

    inputs = [arg.describe() for arg in description.get('arguments', [])]
    spec = {
        'name': description.get('name', task.name),
        'inputs': inputs
    }
    desc = description.get('description', getdoc(func))
    if desc:
        spec['description'] = desc

    return spec


def get_input_data(arg, input):
    if input.get('mode', 'inline') != 'inline' or\
       'data' not in input:
        raise ValueError('Unhandled input mode')

    value = arg.deserialize(input['data'])
    arg.validate(value)
    return value


def parse_inputs(task, inputs):
    func = task.run
    description = get_description_attribute(func)
    arguments = description.get('arguments', [])
    args = []
    kwargs = {}
    for arg in arguments:
        desc = arg.describe()
        id = desc['id']
        name = desc['name']
        if id not in inputs and not arg.has_default():
            raise MissingInputException('Required input "%s" not provided' % name)
        if id in inputs:
            kwargs[name] = get_input_data(arg, inputs[id])
    return args, kwargs
