class Specification(object):
    """
    The base class of the various specifications used for running tasks.
    """
    def __init__(self, obj=None):
        """
        Create a new specification, or unmarshal one from an existing object
        by passing it as the `obj` argument.

        :param obj: An object to unmarshal, or None to build a new spec.
        :type obj: self.baseType or None
        """
        if not hasattr(self, 'baseType'):
            self.baseType = dict

        if obj is None:
            self._obj = self.baseType()
        else:
            self._obj = obj

    def marshal(self):
        """
        Convert this object into its underlying format (e.g. dict, list) for
        consumption by romanesco.run().
        """
        return self._obj


class TaskSpecification(Specification):
    pass


class WorkflowTaskSpecification(TaskSpecification):
    def __init__(self, obj=None, id=None):
        """
        Create a workflow task.

        :param obj: Pass this parameter if you want to unmarshal an existing
            workflow task into an object of this type.
        :type obj: dict or None
        :param id: If you wish to explicitly set an ID for this workflow,
            pass this parameter. Otherwise one will be generated for you. These
            id's must be unique for the entire task.
        """
        TaskSpecification.__init__(self, obj=obj)

        if id is not None:
            self._obj['id'] = id


class InputBindingSpecification(Specification):
    # TODO STUB
    pass


class OutputBindingSpecification(Specification):
    # TODO STUB
    pass
