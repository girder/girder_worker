import six

from .base import Base


class String(Base):

    description = {
        'type': 'string',
        'description': 'Provide a string value'
    }

    def validate(self, value):
        if not isinstance(value, six.string_types):
            raise TypeError('Expected a string value for "%s"' % self.name)
