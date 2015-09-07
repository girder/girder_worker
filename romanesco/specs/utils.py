from romanesco import specs


def spec_class_generator(class_type, spec):

    """Generate a generic Task style class from a Spec style dict.
    For example:

    >>> from romanesco.specs.utils import spec_class_generator
    >>> spec = {
    ...             "inputs": [
    ...                 {"name": "a",
    ...                  "type": "number",
    ...                  "format": "number"}],
    ...             "outputs": [
    ...                 {"name": "b",
    ...                  "type": "number",
    ...                  "format": "number"}],
    ...             "mode": "python",
    ...             "script": "b = a + 3"}

    # Define the class
    >>> spec_class_generator("addThree", spec)
    <class 'romanesco.specs.utils.addThree'>

    # Set a variable to hold the class
    >>> addThree = spec_class_generator("addThree", spec)

    # Instantiate the class
    >>> addThree("task_name") # doctest: +NORMALIZE_WHITESPACE
    {"inputs": [{"format": "number", "name": "a", "type": "number"}],
     "mode": "python",
     "outputs": [{"format": "number", "name": "b", "type": "number"}],
     "script": "b = a + 3"}
    """

    # Decorator that adds 'scirpt' and 'mode' keywords from
    # the spec to the kw argument passed to the decorated function
    def add_spec_to_kw(func):
        def wrapped_f(*args, **kwargs):
            for k in ['script', 'mode', 'steps', 'connections']:
                if k not in kwargs.keys():
                    try:
                        kwargs[k] = spec[k]
                    except KeyError:
                        pass
            func(*args, **kwargs)
        return wrapped_f

    # __init__ function used for the class
    @add_spec_to_kw
    def __init__(self, name, *args, **kw):
        specs.Task.__init__(self, name, *args, **kw)
        for k, v in kw.items():
            setattr(self, k, v)

        return __init__

    # Define __inputs__ and __outputs__ variables on the class.
    cls_vars = {
        "__inputs__": specs.PortList(spec['inputs']),
        "__outputs__": specs.PortList(spec['outputs']),
        "__init__": __init__}

    return type(class_type, (specs.Task,), cls_vars)
