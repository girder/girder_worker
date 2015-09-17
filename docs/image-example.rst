Image processing
----------------

This example will introduce how to use Romanesco to build some simple image
processing tasks using Pillow_.  We will learn how to chain several tasks
together in a workflow and finally how to run these workflows both locally
and through a remote worker.

.. _Pillow: https://python-pillow.github.io/


Download and convert an image
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For our first task, we will download a png image from a public website and
compress it into a jpg.  There are several ways to build tasks in Romanesco;
in this example, we will use the pythonic interface in the :py:mod:`romanesco.specs`
module.


.. literalinclude:: static/image_example.py
