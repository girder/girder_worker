from .number import Number


class Integer(Number):

    paramType = 'integer'

    def __init__(self, *args, **kwargs):
        kwargs['step'] = 1
        super(Integer, self).__init__(*args, **kwargs)

    def serialize(self, value):
        value = super(Integer, self).serialize(value)
        return int(value)
