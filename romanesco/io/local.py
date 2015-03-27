def fetch(spec, **kwargs):
    """
    Fetches a file on the local filesystem into memory.
    """
    with open(spec['path'], 'rb') as f:
        return f.read()
