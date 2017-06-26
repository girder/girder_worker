from .choice import Choice


class StringMultichoice(Choice):
    """Define a multichose string parameter type.

    Values of this type are iterable sequences of strings
    all of which must be an element of a predefined set.

    >>> @app.argument('people', app.types.StringMultichoice, choices=('alice', 'bob', 'charlie'))
    ... @app.task
    ... def func(people=('alice', 'bob')):
    ...     pass
    """

    paramType = 'string-enumeration-multiple'
    multiple = True
