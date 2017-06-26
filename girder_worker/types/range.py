from .number import Number


class Range(Number):
    """Define numeric parameter with valid values in a given range.

    >>> @app.argument('value', app.types.Range, min=10, max=100, step=10)
    ... @app.task
    ... def func(value):
    ...     pass
    """

    paramType = 'range'
