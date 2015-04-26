"""This module defines some simple operations on pandas data."""

from gaia.core import Task


class Operator(Task):

    """Skeleton class for an arbitrary operator.

    For these purposes, an operator takes an arbitrary number of inputs
    and produces one output.  The core operators assume that the data
    types passed support the given operator.  Any type checking is
    left up to either subclasses or the user.

    The inputs are named '0', '1', '2', etc.
    The output is pushed to the default unnamed port, ''.

    The task will execute the method ``operation`` on the first
    argument with positional arguments 1:.

    >>> class Equal(Operator):
    ...     input_ports = {
    ...         '0': Task.make_input_port(object),
    ...         '1': Task.make_input_port(object)
    ...     }
    ...     operation = '__eq__'
    >>> onef = Task.create_source(1.0).get_output()
    >>> onei = Task.create_source(1).get_output()
    >>> equal = Equal().set_input('0', onef).set_input('1', onei)
    >>> equal.get_output_data()
    True
    """

    output_ports = {
        '': Task.make_output_port(object)
    }
    operation = None  #: The operator method to call inside run.

    def run(self, *args, **kw):
        """Execute the operator and populate the output."""
        super(Operator, self).run(*args, **kw)

        # get the input data in a list
        i = 0
        args = []
        while str(i) in self._input_data:
            args.append(self._input_data[str(i)])
            i += 1

        # execute the operator method and store in the output cache
        if not args or not hasattr(args[0], self.operation):
            print args[0]
            print self.operation
            raise Exception('Invalid operation for input type')

        func = getattr(args[0], self.operation)
        self._output_data[''] = func(*args[1:])
        self.dirty = False


class Unary(Operator):

    """Skeleton class for a unary operator."""

    input_ports = {
        '0': Task.make_input_port(object)
    }


class Binary(Operator):

    """Skeleton class for a binary operator."""

    input_ports = {
        '0': Task.make_input_port(object),
        '1': Task.make_input_port(object)
    }


class Add(Binary):

    """Add two objects together.

    >>> two = Task.create_source(2).get_output()
    >>> three = Task.create_source(3).get_output()
    >>> Add().set_input('0', two).set_input('1', three).get_output_data()
    5
    """

    operation = '__add__'


class Subtract(Binary):

    """Subtract two objects.

    >>> two = Task.create_source(2).get_output()
    >>> three = Task.create_source(3).get_output()
    >>> Subtract().set_input('0', two).set_input('1', three).get_output_data()
    -1
    """

    operation = '__sub__'


class Multiply(Binary):

    """Multiply two objects together.

    >>> two = Task.create_source(2).get_output()
    >>> three = Task.create_source(3).get_output()
    >>> Multiply().set_input('0', two).set_input('1', three).get_output_data()
    6
    """

    operation = '__mul__'


class Divide(Binary):

    """Divide two objects.

    >>> six = Task.create_source(6).get_output()
    >>> three = Task.create_source(3).get_output()
    >>> Divide().set_input('0', six).set_input('1', three).get_output_data()
    2
    """

    operation = '__div__'


class Fork(Task):

    """Copy the input into one or more outputs.

    >>> msg = Task.create_source("This is a message").get_output()
    >>> fork = Fork().set_input(port=msg)
    >>> fork.get_output_data(name='0')
    'This is a message'
    >>> fork.get_output_data(name='1')
    'This is a message'
    """

    input_ports = {
        '': Task.make_input_port(object)
    }
    output_ports = {
        '0': Task.make_output_port(object),
        '1': Task.make_output_port(object)
    }

    def run(self, *args, **kw):
        """Copy inputs to outputs."""
        super(Fork, self).run(*args, **kw)

        for i in self.output_ports:
            self._output_data[i] = self._input_data['']

        self.dirty = False

# Too low level, probably.
#  class GetAttr(Unary):
#
#      """Get an attribute from an object.
#
#      >>> cmplx = Task.create_source(1 - 1j).get_output()
#      >>> GetAttribute(attr='imag').set_input(port=cmplx).get_output_data()
#      -1.0
#      """
#
#      operation = '__getattribute__'
#
#  GetAttribute.add_property('attr')
#
#
#  class GetItem(Unary):
#
#      """Get an attribute from an object.
#
#      >>> a_dict = Task.create_source({'a': 'b'}).get_output()
#      >>> GetItem(item='a').set_input('0', a_dict).get_output_data()
#      'b'
#      """
#
#      operation = '__getitem__'
#
#  GetItem.add_property('item')
