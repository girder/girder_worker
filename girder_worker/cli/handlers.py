from functools import wraps
import json

def gwrun_output_handler(func):
    @wraps(func)
    def _handler(value, **kwargs):
        # Call the function for its output side effects
        func(value, **kwargs)

        # Return the value unmodified
        return value

    return _handler


@gwrun_output_handler
def stdout_output_handler(value):
    print(value)


@gwrun_output_handler
def json_output_handler(value):
    print(json.dumps(value))
