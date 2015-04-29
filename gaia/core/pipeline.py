"""This module defines a task pipeline used by Gaia."""

from gaia.core.base import GaiaObject


class Pipeline(GaiaObject):

    """A pipeline is an array of connected tasks.

    This class largely serves to provide various graph algorithms to task
    pipelines.
    """

    def __init__(self, task):
        """Construct a pipeline object from all tasks connected to the given task."""
        self._task = task

    @property
    def tasks(self):
        """Return all connected tasks."""
        pass

    @property
    def inputs(self):
        """Return all unconnected input ports."""
        pass

    @property
    def input_tasks(self):
        """Return all tasks with unconnected input ports."""
        pass

    @property
    def outputs(self):
        """Return all unconnected output ports."""
        pass

    @property
    def output_tasks(self):
        """Return all tasks with unconnected output ports."""
        pass

    @property
    def interior(self):
        """Return all tasks with no unconnected ports."""
        pass
