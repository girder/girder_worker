from .vector import Vector
from .number import Number


class NumberVector(Vector):
    """Define a parameter accepting a list of numbers.

    >>> @app.argument('value', app.types.NumberVector, min=10, max=100, step=10)
    ... @app.task
    ... def func(value=(10, 11)):
    ...     pass
    """

    paramType = 'number-vector'
    elementClass = Number
