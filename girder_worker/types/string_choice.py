from .choice import Choice


class StringChoice(Choice):
    """Define a string parameter with a list of valid values.

    >>> @app.argument('person', app.types.StringChoice, choices=('alice', 'bob', 'charlie'))
    ... @app.task
    ... def func(person):
    ...     pass
    """

    paramType = 'string-enumeration'
