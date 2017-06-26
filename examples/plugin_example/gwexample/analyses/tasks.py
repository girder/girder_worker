from girder_worker.app import app


@app.task
@app.argument('n', app.types.Integer)
def fibonacci(n):
    """Compute the nth fibonacci number recursively."""
    if n == 1 or n == 2:
        return 1
    return fibonacci(n-1) + fibonacci(n-2)
