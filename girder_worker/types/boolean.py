from .base import Base


class Boolean(Base):

    description = {
        'type': 'boolean',
        'description': 'Provide a boolean value'
    }

    def serialize(self, value):
        return bool(value)
