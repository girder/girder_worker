import numbers
import six

from .base import Base


class Number(Base):

    paramType = 'number'

    def __init__(self, *args, **kwargs):
        super(Number, self).__init__(*args, **kwargs)
        self.min = kwargs.get('min')
        self.max = kwargs.get('max')
        self.step = kwargs.get('step')

    def describe(self, **kwargs):
        desc = super(Number, self).describe(**kwargs)

        if self.min is not None:
            desc['min'] = self.min
        if self.max is not None:
            desc['max'] = self.max
        if self.step is not None:
            desc['step'] = self.step

        desc['type'] = self.paramType
        desc['description'] = self.help or 'Select a number'
        return desc

    def validate(self, value):
        if not isinstance(value, numbers.Number):
            raise TypeError('Expected a number for parameter "%s"' % self.name)

        if self.min is not None and value < self.min:
            raise ValueError('Expected %s <= %s' % (str(self.min), str(value)))

        if self.max is not None and value > self.max:
            raise ValueError('Expected %s >= %s' % (str(self.max), str(value)))

    def serialize(self, value):
        if self.step is not None:
            n = round(float(value) / self.step)
            value = n * self.step
        return value

    def deserialize(self, value):
        if isinstance(value, six.string_types):
            value = float(value)
        return value
