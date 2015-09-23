Image processing
----------------

This example will introduce how to use Romanesco to build some simple image
processing tasks using Pillow_.  We will learn how to chain several tasks
together in a workflow and finally how to run these workflows both locally
and through a remote worker.

.. _Pillow: https://python-pillow.github.io/


.. testsetup::

   import romanesco
   from PIL.Image import Image

Download and view an image
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For our first task, we will download a png image from a public website and
display it on the screen.  We begin by defining a new task that will take
a single image object and call its ``show`` method.

A Romanesco task is a special kind of dictionary with keys ``inputs`` and
``outputs`` as well as other metadata describing how these objects will be
used.  In the case of simple python scripts, they can be provided inline as
we have done in this example.  Each input and output spec in a task is a dict
with the following keys:

``name``
   The name designated to the datum.  This is used both for connecting tasks
   together in a workflow and, in the case of python tasks, the name of the
   variable injected into/extracted from the tasks scope.

``type``
   The general data type expected by the task.  See :ref:`types-and-formats`
   for a list of types provided by Romanesco's core library as well as
   :ref:`romanesco-plugins` for additional data types provided by optional
   plugins.

``format``
   The specific representation or encoding of the data type.  Romanesco will
   automatically convert between different data formats provided that they
   are of the same base type.

.. testcode::

   show_image = {
       'inputs': [{'name': 'the_image', 'type': 'image', 'format': 'pil'}],
       'outputs': [],
       'script': 'the_image.show()'
   }

In order to run the task, we will need to provide an :ref:`input binding <input-spec>`
that tells Romanesco where it can get the data to be injected into the port.  Several
I/O modes are supported; in this case, we provide a public URL to an image that
Romanesco will download and open using Pillow.  Notice that Romanesco downloads and
reads the file as part of the automatic data format conversion.

.. testcode::

   lenna = {
       'type': 'image',
       'format': 'png',
       'url': 'https://upload.wikimedia.org/wikipedia/en/2/24/Lenna.png'
   }

.. testcode::
   :hide:

   # here we replace the show image task to a no-op so we can test without
   # a display
   show_image = {
       'inputs': [{'name': 'the_image', 'type': 'image', 'format': 'pil'}],
       'outputs': [{'name': 'the_image', 'type': 'image', 'format': 'pil'}],
       'script': 'pass'
   }

Finally to run this task, we only need to provide the task object and the input binding to
:func:`romanesco.run`.  The object returned by this function contains data extracted
and converted through the task's output ports.

.. testcode::

   output = romanesco.run(show_image, {'the_image': lenna})

.. doctest::
   :hide:

   >>> isinstance(output['the_image']['data'], Image)
   True
