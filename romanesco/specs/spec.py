"""Define the common parent type for all json specs contained in the package."""

import six
import json


class Spec(dict):

    r"""
    Defines core utility methods that all spec objects have in common.

    Supports dict-like initialization.
    >>> a = Spec({'a': 1, 'b': {'c': [1, 2, None]}})
    >>> b = Spec(a=1, b={'c': [1, 2, None]})
    >>> a == b
    True

    Also supports initialization from json
    >>> c = Spec('{"a": 1, "b": {"c": [1, 2, null]}}')
    >>> a == c
    True

    Serialization is done with json
    >>> str(a)
    '{"a": 1, "b": {"c": [1, 2, null]}}'

    Strings are assumed to be utf-8 encoded.
    >>> str(Spec({u"for\u00eat": u"\ud83c\udf33 \ud83c\udf32 \ud83c\udf34"}))
    '{"for\\u00eat": "\\ud83c\\udf33 \\ud83c\\udf32 \\ud83c\\udf34"}'
    """

    def __init__(self, *args, **kw):
        """Extend the standard dict __init__ to allow json input as well.

        If called with a string argument, this method will attempt to parse the
        string with json.loads.  Otherwise, the arguments are passed directly
        to :py:func:`dict.__init__`.
        """
        if len(args) and isinstance(args[0], six.string_types):
            super(Spec, self).__init__(json.loads(*args, **kw))
        else:
            super(Spec, self).__init__(*args, **kw)

    def json(self, **kw):
        """Return the spec as a json blob.

        Keyword arguments are passed to :py:func:`json.dumps`.
        """
        return json.dumps(self, **kw)

    def __str__(self):
        """Serialize the object as json."""
        return self.json(default=str, skipkeys=True)
