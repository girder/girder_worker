from girder_worker.app import app
from girder_worker.describe import argument, types


@app.task
@argument('n', types.Integer, min=1)
def fibonacci(n):
    """Compute the nth fibonacci number recursively."""
    if n == 1 or n == 2:
        return 1
    return fibonacci(n-1) + fibonacci(n-2)
