import six

from inspect import getdoc
try:
    from inspect import signature
except ImportError:
    from funcsigs import signature

from . import types


class MissingDescriptionException(Exception):
    pass


class MissingInputException(Exception):
    pass


def get_description_attribute(func):
    description = getattr(func, '_girder_description', None)
    if description is None:
        raise MissingDescriptionException('Task is missing description decorators')
    return description


def argument(name, type):
    """Describe an argument to a task."""

    if not isinstance(name, six.string_types):
        raise TypeError('Expected argument name to be a string')

    if isinstance(type, six.string_types):
        if type not in types:
            raise ValueError('Unknown argument type "%s"' % type)

        type = types[type](name)

    def argument_wrapper(func):
        func._girder_description = getattr(func, '_girder_description', {})
        args = func._girder_description.setdefault('arguments', {})
        sig = signature(func)

        if name not in sig.parameters:
            raise ValueError('Invalid argument name "%s"' % name)

        type.set_parameter(sig.parameters[name], signature=sig)
        args[name] = type

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


def parse_inputs(task, inputs):
    func = task.run
    description = get_description_attribute(func)
    arguments = description.get('arguments', [])
    kwargs = {}
    for arg in arguments:
        desc = arg.describe()
        id = desc['id']
        name = desc['name']
        if id not in inputs and not arg.has_default():
            raise MissingInputException('Required input "%s" not provided' % name)
        if id in inputs:
            kwargs[name] = arg.deserialize(inputs[id])
    return kwargs
