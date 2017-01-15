Image processing
----------------

This example will introduce how to use the Girder Worker to build some simple image
processing tasks using Pillow_.  We will learn how to chain several tasks
together in a workflow and finally how to run these workflows both locally
and through a remote worker.

.. _Pillow: https://python-pillow.github.io/


.. testsetup::

   import os
   import girder_worker.tasks
   from girder_worker import PACKAGE_DIR, core
   from PIL.Image import Image
   core.utils.load_plugin('types', [os.path.join(PACKAGE_DIR, 'plugins')])


Download and view an image
~~~~~~~~~~~~~~~~~~~~~~~~~~

For our first task, we will download a png image from a public website and
display it on the screen.  We begin by defining a new task that will take
a single image object and call its ``show`` method.

A task is a special kind of dictionary with keys ``inputs`` and
``outputs`` as well as other metadata describing how these objects will be
used.  In the case of simple Python scripts, they can be provided inline as
we have done in this example.  Each input and output spec in a task is a dict
with the following keys:

``name``
   The name designated to the datum.  This is used both for connecting tasks
   together in a workflow and, in the case of Python tasks, the name of the
   variable injected into/extracted from the tasks scope.

``type``
   The general data type expected by the task.  See :ref:`types-and-formats`
   for a list of types provided by the worker's core library as well as
   :ref:`worker-plugins` for additional data types provided by optional
   plugins.

``format``
   The specific representation or encoding of the data type. The worker will
   automatically convert between different data formats provided that they
   are of the same base type.

.. testcode::

   show_image = {
       'inputs': [{'name': 'the_image', 'type': 'image', 'format': 'pil'}],
       'outputs': [],
       'script': 'the_image.show()'
   }

In order to run the task, we will need to provide an :ref:`input binding <input-spec>`
that tells the worker where it can get the data to be injected into the port.  Several
I/O modes are supported; in this case, we provide a public URL to an image that
the worker will download and open using Pillow.  Notice that the worker downloads and
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
:func:`girder_worker.tasks.run`.  The object returned by this function contains data extracted
and converted through the task's output ports.

.. testcode::

   output = girder_worker.tasks.run(show_image, {'the_image': lenna})

.. doctest::
   :hide:

   >>> isinstance(output['the_image']['data'], Image)
   True


Perform an image blur inside a workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now that we know how to generate a simple task using the worker, we
want to learn how to connect multiple tasks together in a workflow.
The worker's pythonic API allows us to do this easily. Let's create
a new task that performs a blur operation on an image. This might
look like the following:

.. testcode::

   blur_image = {
      'inputs': [
         {'name': 'blur_input', 'type': 'image', 'format': 'pil'},
         {'name': 'blur_radius', 'type': 'number', 'format': 'number'}
      ],
      'outputs': [{'name': 'blur_output', 'type': 'image', 'format': 'pil'}],
      'script': """
   from PIL import ImageFilter
   blur_output = blur_input.filter(ImageFilter.GaussianBlur(blur_radius))
   """
   }

Notice that this task takes an additional numeric input that acts as
a parameter for the blurring filter.  Connecting our ``show_image``
task, we can view the result of our image filter.  First, we create
a new workflow object from the :mod:`girder_worker.core.specs` module.

.. testcode::

   from girder_worker.core.specs import Workflow
   wf = Workflow()

Next, we add all the tasks to the workflow.  The order in which the tasks
are added is insignificant because the worker will automatically sort them
according to their position in the workflow.

.. testcode::

   wf.add_task(blur_image, 'blur')
   wf.add_task(show_image, 'show')

Finally, we connect the two tasks together.

.. testcode::

   wf.connect_tasks('blur', 'show', {'blur_output': 'the_image'})

Running a workflow has the same syntax as running a single task.

.. testcode::

   output = girder_worker.tasks.run(
      wf,
      inputs={
         'blur_input': lenna,
         'blur_radius': {'format': 'number', 'data': 5}
      }
   )

.. |lenna| image:: static/lenna.jpg
   :width: 100%

.. |lenna10| image:: static/lenna10.jpg
   :width: 100%

.. table:: Blur image workflow

   +-----------+-----------+
   | |lenna|   | |lenna10| |
   +-----------+-----------+

.. testoutput::
   :hide:

   --- beginning: blur ---
   --- finished: blur ---
   --- beginning: show ---
   --- finished: show ---

.. doctest::
   :hide:

   >>> isinstance(output['the_image']['data'], Image)
   True

Using a workflow to compute image metrics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finally, we will create a few more tasks to generate a more complicated
workflow that returns some number of interest about an image.  First, let's
create a task to subtract two images from each other.

.. testcode::

   subtract_image = {
       'inputs': [
           {'name': 'sub_input1', 'type': 'image', 'format': 'pil'},
           {'name': 'sub_input2', 'type': 'image', 'format': 'pil'}
       ],
       'outputs': [
           {'name': 'diff', 'type': 'image', 'format': 'pil'},
       ],
       'script': """
   from PIL import ImageMath
   diff = ImageMath.eval('abs(int(a) - int(b))', a=sub_input1, b=sub_input2)
   """
   }

Now another task will compute the average pixel value of the input image.

.. testcode::

   mean_image = {
       'inputs': [
           {'name': 'mean_input', 'type': 'image', 'format': 'pil'},
       ],
       'outputs': [
           {'name': 'mean_value', 'type': 'number', 'format': 'number'},
       ],
       'script': """
   from PIL import ImageStat
   mean_value = ImageStat.Stat(mean_input).mean[0]
   """
   }

Finally, let's add all of the tasks to a new workflow and make the appropriate connections.

.. testcode::

   wf = Workflow()
   wf.add_task(blur_image, 'blur1')
   wf.add_task(blur_image, 'blur2')
   wf.add_task(subtract_image, 'subtract')
   wf.add_task(mean_image, 'mean')

   wf.connect_tasks('blur1', 'subtract', {'blur_output': 'sub_input1'})
   wf.connect_tasks('blur2', 'subtract', {'blur_output': 'sub_input2'})
   wf.connect_tasks('subtract', 'mean', {'diff': 'mean_input'})

This workflow performs blurring operations on a pair of input images, computes the difference
between them, and returns the average value of the difference.  Let's see how this works with
our sample image.  Notice that in this case, there is a conflict between the input port names
of the two ``blur`` tasks.  We must specify which port we are referring to by prefixing the
port name with the task name.

.. testcode::

   output = girder_worker.tasks.run(
      wf,
      inputs={
         'blur1.blur_input': lenna,
         'blur1.blur_radius': {'format': 'number', 'data': 1},
         'blur2.blur_input': lenna,
         'blur2.blur_radius': {'format': 'number', 'data': 8},
      }
   )
   print output['mean_value']['data']

.. testoutput::
   :hide:
   :options: +ELLIPSIS

   --- beginning: blur1 ---
   --- finished: blur1 ---
   --- beginning: blur2 ---
   --- finished: blur2 ---
   --- beginning: subtract ---
   --- finished: subtract ---
   --- beginning: mean ---
   --- finished: mean ---
   27.7978668213
