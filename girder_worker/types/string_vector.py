from .vector import Vector
from .string import String


class StringVector(Vector):
    """Define a parameter which takes a list of strings.

    >>> @app.argument('people', app.types.StringVector)
    ... @app.task
    ... def func(people=('alice', 'bob')):
    ...     pass
    """

    paramType = 'string-vector'
    elementClass = String
