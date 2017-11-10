import select


def select_loop(exit_condition=lambda: True, readers=None, writers=None):
    """
    Run a select loop for a set of readers and writers

    :param exit_condition: A function to evaluate to determine if the select
        loop should terminate if all pipes are empty.
    :type exit_condition: function
    :param readers: The list of ReaderStreamConnector's that will be added to the
        select call..
    :type readers: list
    :param writers: The list of WriteStreamConnector's that will be added to the
        select call..
    :type writers: list
    """

    BUF_LEN = 65536

    try:
        while True:
            # We evaluate this first so that we get one last iteration of
            # of the loop before breaking out of the loop.
            exit = exit_condition()

            open_writers = [writer for writer in writers if writer.fileno() is not None]

            # get ready pipes, timeout of 100 ms
            readable, writable, _ = select.select(readers, open_writers, (), 0.1)

            for ready in readable:
                read = ready.read(BUF_LEN)
                if read == 0:
                    readers.remove(ready)

            for ready in writable:
                # TODO for now it's OK for the input reads to block since
                # input generally happens first, but we should consider how to
                # support non-blocking stream inputs in the future.
                written = ready.write(BUF_LEN)
                if written == 0:
                    writers.remove(ready)

            need_opening = [writer for writer in writers if writer.fileno() is None]
            for connector in need_opening:
                connector.open()

            # all pipes empty?
            empty = (not readers or not readable) and (not writers or not writable)

            if (empty and exit):
                break

    finally:
        for stream in readers + writers:
            stream.close()


class StreamPushAdapter(object):
    """
    This represents the interface that must be implemented by push adapters for
    IO modes that want to implement streaming output.
    """
    def __init__(self, output_spec):
        """
        Initialize the adpater based on the output spec.
        """
        self.output_spec = output_spec

    def write(self, buf):
        """
        Write a chunk of data to the output stream.
        """
        raise NotImplemented

    def close(self):
        """
        Close the output stream. Called after the last data is sent.
        """
        pass


class WritePipeAdapter(StreamPushAdapter):
    """
    Simply wraps another pipe that contains a ``write`` method. This is useful
    for wrapping ``sys.stdout`` and ``sys.stderr``, where we want to call
    ``write`` but not ``close`` on them.
    """
    def __init__(self, output_spec, pipe):
        """
        :param pipe: An object containing a ``write`` method, e.g. sys.stdout.
        """
        super(WritePipeAdapter, self).__init__(output_spec)
        self.pipe = pipe

    def write(self, buf):
        self.pipe.write(buf)
