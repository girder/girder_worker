def fetch(spec, **kwargs):
    """
    Fetches a file on the local filesystem into memory.
    """
    with open(spec['path'], 'rb') as f:
        return f.read()


def push(data, spec, **kwargs):
    """
    Write a blob of data in memory to a file specified in ``spec['path']``.
    """
    with open(spec['path'], 'wb') as out:
        out.write(data)
