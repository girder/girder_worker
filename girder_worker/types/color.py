from .base import Base


class Color(Base):
    """Define a task parameter expecting a color value.

    >>> @app.argument('background', app.types.Color)
    ... @app.task
    ... def func(background):
    ...     pass
    """

    description = {
        'type': 'color',
        'description': 'Provide a color value'
    }

    # TODO: handle normalization and validation
