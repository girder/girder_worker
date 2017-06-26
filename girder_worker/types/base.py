from copy import deepcopy


class Base(object):

    description = {}

    def __init__(self, name, **kwargs):
        self.id = kwargs.get('id', name)
        self.name = name
        self.help = kwargs.get('help')

    def set_parameter(self, parameter, **kwargs):
        self.parameter = parameter

    def has_default(self):
        return self.parameter.default is not self.parameter.empty

    def describe(self):
        copy = deepcopy(self.description)
        copy.setdefault('id', self.id)
        copy.setdefault('name', self.name)
        if self.has_default():
            copy.setdefault('default', {
                'data': self.serialize(self.parameter.default)
            })
        if self.help is not None:
            copy['description'] = self.help
        return copy

    def serialize(self, value):
        return value

    def deserialize(self, value):
        return value

    def validate(self, value):
        pass
