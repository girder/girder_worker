import six

from .base import Base


class Vector(Base):

    paramType = None
    elementClass = None
    seperator = ','

    def __init__(self, *args, **kwargs):
        if self.paramType is None:
            raise NotImplementedError('Subclasses should define paramType')

        if self.elementClass is None:
            raise NotImplementedError('Subclasses should define elementClass')

        self.element = self.elementClass(*args, **kwargs)
        super(Vector, self).__init__(*args, **kwargs)

    def describe(self, *args, **kwargs):
        desc = super(Vector, self).describe(*args, **kwargs)
        desc['type'] = self.paramType
        desc['description'] = 'Provide a list of values'
        return desc

    def validate(self, value):
        if not isinstance(value, (list, tuple)):
            raise TypeError('Expected a list or tuple for "%s"' % self.name)

        for elementValue in value:
            self.element.validate(elementValue)

    def deserialize(self, value):
        if isinstance(value, six.string_types):
            value = value.split(self.seperator)

        return [self.element.deserialize(v) for v in value]
