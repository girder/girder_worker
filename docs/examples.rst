Examples
==============================================

Before getting started, make sure you've followed the necessary steps when it comes to
:doc:`installation` of Romanesco.


Visualize Facebook data with Romanesco
----------------------------------------

This example demonstrates how to use Romanesco as a workflow system to load graph data,
perform analyses and transformations of the data using
`NetworkX <https://networkx.github.io/>`_, and then visualize the result
using `d3.js <http://d3js.org/>`_.


In this example we will:
 1. Obtain a set of Facebook data
 2. Find the most "popular" person in our data
 3. Find the subgraph of the most popular person's neighborhood
 4. Visualize this neighborhood using d3

Obtain Dataset
~~~~~~~~~~~~~~

The dataset is a small sample of Facebook links representing friendships, which can be obtained `here <_static/facebook-sample-data.txt>`__ [#f1]_.

The data we'll be using is in a format commonly used when dealing with graphs, referred to as an `adjacency list <https://en.wikipedia.org/wiki/Adjacency_list>`_. Romanesco supports using adjacency lists with graphs out of the box.

.. note :: A full list of the types and formats that Romanesco supports is documented in :doc:`types-and-formats`.

Here is a sample of what the data looks like:

.. code-block:: none

       86      127
       303     325
       356     367
       373     404
       475     484

Each integer represents an anonymized Facebook user. Users belonging to the same line in the adjacency list indicates a symmetric relationship in our undirected graph.

Build a Workflow
~~~~~~~~~~~~~~~~

Create a file named ``workflow.py``, this is the file we'll be using to create our Romanesco workflow.

Finding the Most Popular Person
###############################
One way of measuring who the most "popular" person in our graph is, is by taking the node with the largest
`degree <https://en.wikipedia.org/wiki/Degree_%28graph_theory%29>`_.

The script below finds the most popular person in the graph.

.. note :: This script assumes a variable ``G`` exists, that's because we define it as an input in the ``Task`` we define in the next step.

.. literalinclude:: static/facebook-example-most-popular.py
    :linenos:

Defining our Romanesco task, we can embed this script:

.. literalinclude:: static/facebook-example.py
    :caption: workflow.py/most_popular_task
    :lines: 1-25
    :linenos:

.. note :: As we saw with our last script assuming ``G`` would in be scope, this task explicitly states that both ``most_popular_person`` and ``G`` will be in scope (as its outputs) when it's done.


Finding Their Neighborhood
##########################
Now that we have the most popular node in the graph, we can take the `subgraph <https://en.wikipedia.org/wiki/Glossary_of_graph_theory#Subgraphs>`_ including only this person and all of their neighbors. These are
sometimes referred to as `Ego Networks <http://www.analytictech.com/networks/egonet.htm>`_.

.. literalinclude:: static/facebook-example-find-neighborhood.py
    :linenos:

Again, we can create a Romanesco task using our new script, like so:

.. note :: Since these steps are going to be connected, our inputs are going to be the same as the last steps outputs.

.. literalinclude:: static/facebook-example.py
    :caption: workflow.py/find_neighborhood_task
    :lines: 24-44
    :lineno-start: 27
    :linenos:


Putting It Together
###################
Conceptually, this is what our workflow will look like:

.. image:: static/facebook-example-workflow.png
    :align: center
    :alt: Visualize Facebook Data Workflow Diagram

\* The format changes because of Romanescos auto-conversion functionality.

The entire rectangle is our workflow, and the blue rectangles are our tasks. Black arrows represent inputs and outputs and the red arrows represent connections which we’ll see shortly.


To make this happen, since we've written the tasks already, we just need to format this in a way Romanesco understands.

To start, let's create our workflow from a high level, starting with just its inputs and outputs (the black arrows):

.. literalinclude:: static/facebook-example.py
    :caption: workflow.py/workflow
    :lines: 46-58
    :lineno-start: 46
    :linenos:

Now we need to add our tasks to the workflow, which is pretty straightforward since we've defined them in the previous steps.

.. literalinclude:: static/facebook-example.py
    :caption: workflow.py/workflow_tasks
    :lines: 60-63
    :lineno-start: 60
    :linenos:

Finally, we need to add the red arrows within the workflow, telling Romanesco how the inputs and outputs are going to flow from each task. These are called *connections* in Romanesco.

.. literalinclude:: static/facebook-example.py
    :caption: workflow.py/workflow_connections
    :lines: 65-80
    :lineno-start: 65
    :linenos:


We now have a complete workflow! Let's run this, and write the final data to a file.

.. literalinclude:: static/facebook-example.py
    :caption: workflow.py/run
    :lines: 82-91
    :lineno-start: 82
    :linenos:

Running ``workflow.py`` will produce the JSON in a file called ``data.json``, which we'll pass to d3.js in the next step.

.. note :: More information on Romanesco Tasks and Workflows can be found in :doc:`api-docs`.


Visualize the Results
~~~~~~~~~~~~~~~~~~~~~

Using JavaScript similar to `this d3.js example <http://bl.ocks.org/mbostock/4062045>`_ we're going to add the following to our ``index.html`` file:

.. literalinclude:: static/facebook-example.html
    :linenos:

Which should leave us with a visualization similar to the following:

.. raw:: html

   <div id="popularity-graph"></div>


This is of course a more verbose than necessary workflow for the purposes of demonstration. This could have easily been done with one task,
however by following this you should have learned how to do the following with Romanesco:

 * Create Romanesco tasks which consume and produce multiple inputs and outputs
 * Run Romanesco tasks as part of a multi-step workflow
 * Use Romanescos converter system to serialize it in a format JavaScript can read 
 * Visualize the data using d3.js



.. [#f1] For attribution refer `here <http://socialnetworks.mpi-sws.org/data-wosn2009.html>`_.
