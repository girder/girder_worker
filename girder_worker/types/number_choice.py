from .choice import Choice


class NumberChoice(Choice):
    """Define a numeric parameter with a set of valid values.

    >>> @app.argument('address', app.types.NumberChoice, choices=(5, 10, 15))
    ... @app.task
    ... def func(address):
    ...     pass
    """

    paramType = 'number-enumeration'
