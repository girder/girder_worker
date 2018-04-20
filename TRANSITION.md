# Transitioning Legacy Girder Worker Tasks

Transitioning legacy girder worker tasks to the modern framework should be a relatively painless procedure. In broad strokes, the process can be divided into two areas of concern. The first is code changes, and the second is deployment changes. For a more detailed description of the motivation behind these changes, please read the [HACKING](HACKING.md) document.

There are slightly different steps based on the `mode` your legacy task defines.

## "Python" Mode Legacy Tasks

Python mode legacy tasks rely on the python executor to evaluate (i.e. run `eval`) on arbitrary code defined in the task dictionary. In general terms, to convert the task we must transition this code string into an actual function (a.k.a 'task') that is a part of a python package. The package must then be installed in the girder_worker python environment (e.g virtualenv, docker container, etc) and the girder python environment. Code inside the girder requestHandler (or boundHandler) related to creating and scheduling a job will be converted to use the task function defined in the package. Optionally, if the task requires access to files/metadata in girder, transformation classes should be written to handle moving data into and out of the task.

To summarize, migrating python tasks is a three step process:

1. Code Change: Transition the task(s) code into a Python package.
2. Deployment Change: Install the package in both the girder and girder_worker environments.
3. Code Change: Convert Girder-side code that schedules the job to use the task
  1. Optionally: Write transformation classes to handle data I/O with Girder.

_Note_: It is best to perform the following steps in a virtual environment.

### Transitioning code into a Python Package.

First create a package using [Girder Worker plugin cookiecutter](https://github.com/girder/cookiecutter-gw-plugin). To do this you must first install [cookiecutter](https://github.com/girder/cookiecutter-gw-plugin):

```sh
$> pip install cookiecutter
```

Then run the cookiecutter code:

```sh
$> cookiecutter https://github.com/girder/cookiecutter-gw-plugin
```

This will prompt for a number of values to template into the package (See: [Template Variables](https://github.com/girder/cookiecutter-gw-plugin#template-variables) for a description of how each variable is used):

```
author_name [Kitware Inc]:
email [kitware@kitware.com]:
plugin_name [GW Task Plugin]: Example Plugin
plugin_slug [example_plugin]:
plugin_camel [ExamplePlugin]:
plugin_short_description [Boilerplate for creating a Girder Worker Task plugin]: This is an example
version [0.0.0]:
Select open_source_license:
1 - Apache Software License 2.0
2 - MIT license
3 - BSD license
4 - ISC license
5 - GNU General Public License v3
6 - Not open source
Choose from 1, 2, 3, 4, 5, 6 [1]: 1
```

This will generate a directory based on the `plugin_slug` value (in this case `example_plugin/`).

```
.
├── example_plugin
│   ├── __init__.py
│   └── tasks.py
├── README.rst
└── setup.py
```

Code for your task should be placed into the `example_plugin/tasks.py` file. On template creation this will contain the following code:

```python
from girder_worker.app import app
from girder_worker.utils import girder_job

# TODO: Fill in the function with the correct argument signature
# and code that performs the task.
@girder_job(title='Example Task')
@app.task(bind=True)
def example_task(self):
    pass
	
# Note that other tasks may defined here as well.
```

You will want to change the name of the task from `example_task` to something that meaningfully represents what the task does. Additionally arguments and keyword arguments should be added to the task function signature that are appropriate to your task. (Note: see the [Transforms]() section for how to handle arguments that will be data from Girder).

### Install the package

If your package is very simple it maybe ready to install.

```sh
$> cd /root/directory/of/package/
$> pip install .
# Or, alternately, perform an editable install. e.g
# pip install -e .
```

Depending on your task you may have to make other modifications in the package setup.py for the task to function (e.g. defining dependencies etc). Note that the cookiecutter just creates boilerplate code and that any or all of it may be modified as needed.

Unfortunately deployment of your particular project is beyond the scope of this document. For this section to be complete it will be necessary that you can import the task you have defined in both the Girder and Girder Worker environments. *Keep in mind* that some of the deploy time configuration for your Girder Worker instance(s) should move into your package (e.g python dependencies used in the task). This configuration will be brought in when you pip install your package in the Girder Worker environment.

In some complex cases it may make sense to include configuration management scripts in the package and then call out to these scripts from within the larger deployment of Girder Worker.


### Convert Girder-side 'Job' code

Girder-side Job code often looks like the following:

```python
from girder.plugins.jobs.models.job import Job
from girder.plugins.worker import utils

# Define the analysis
girder_worker_run_analysis = {
    'name': 'add',
    'inputs': [
        {'name': 'a', 'type': 'integer', 'format': 'integer', 'default':
         {'format': 'json', 'data': '0'}},
        {'name': 'b', 'type': 'integer', 'format': 'integer'}
    ],
    'outputs': [{'name': 'c', 'type': 'integer', 'format': 'integer'}],
    'script': 'c = a + b',
    'mode': 'python'}

# Define the inputs
girder_worker_run_inputs = {'a': {'format': 'integer', 'data': 1},
                            'b': {'format': 'integer', 'data': 2}}

# Define the outputs
girder_worker_run_outputs = {'c': {'format': 'integer'}}

# Create the job
job = Job().createJob(
    title='Add a and b',
    handler='worker_handler',
    user=self.getCurrentUser(),
	public=False,
	args=(girder_worker_run_analysis,),
    kwargs={'inputs': self.girder_worker_run_inputs,
            'outputs': self.girder_worker_run_outputs})

# Set up the jobInfoSpec
job['kwargs']['jobInfo'] = utils.jobInfoSpec(job)

# Save the Job
Job().save(job)

# Schedule the Job
Job().scheduleJob(job)

return job

```

All of this is necessary to execute the script `c = a + b` on the arguments `a = 1` and `b = 2`. Assuming that we have a task function `my_task` in `my_package.tasks` with following code:

```python
from girder_worker.app import app
from girder_worker.utils import girder_job

@girder_job(title='Add a and b')
@app.task(bind=True)
def my_task(self, a, b):
	return a + b
```

Then the legacy code above may be rewritten as follows:

```python
from my_package.tasks import my_task

async_result = my_task.delay(1, 2)

return async_result.job
```

All `Job` related code is removed in favor of importing the task directly, and using the [Celery API for calling tasks](https://github.com/girder/girder_worker/blob/transition-document/HACKING.md#the-celery-method). Girder Worker has been refactored to move all job related code inside the application. Various knobs and dials have been exposed to allow modifying aspects of the Girder Job that is created. For instance you may set the title of the job at call time by using the `girder_job_title` special keyword argument:

```python
from my_package.tasks import example_task

async_result = my_task.delay(
    1, 2, girder_job_title="A Custom Job Title")

return async_result.job
```

For more details about manipulating Job attributes, please read [The Celery Method](https://github.com/girder/girder_worker/blob/transition-document/HACKING.md#the-celery-method) section of the HACKING document.


### Transforms

The previous steps are sufficient for converting legacy Girder Worker tasks into modern Celery based tasks. If however your task requires access to information inside Girder, then it is recommended that you include "Transform" classes with your package.

Transforms are instantiated inside Girder and their state is serialized as apart of Celery task call. These are deserialized inside Girder Worker and the transform method is called right before execution of the task code. *The result of the transform method is what is passed to the task function*. This allows the transform method to perform side-effect style code that downloads data or metadata and passes that data to the task function.

Consider the following task function:

```python
from girder_worker.app import app

@app.task(bind=True)
def my_task(self, input_file_path):
    with open(input_file_path, 'r') as fp:
	    data = fp.read()
		# Do stuff with data
```

This function may be called directly with a file path:

```python
from my_package.tasks import my_task

my_task.delay('/file/path/that/must/exist/in/girder/worker.txt')
```

_Note_ The file path passed must be available on the girder worker instance.

However, Girder worker's utilities includes the `GirderFileId` transform, which makes a Girder file available in the context of an executing task. To use this Transform from within Girder you can do the following:

```python
from girder_worker_utils.transforms.girder_io import GirderFileId
from my_package.tasks import my_task

# Assume file_id is made available through a requestHandler

my_task.delay(GirderFileId(file_id))
```

Launching this task follows the same pattern as before, but rather than passing in a file path, we pass in a `GirderFileId` object, which will return a file path to a temporary file on the Girder Worker instance after downloading the file with Girder client.

Finally, after the task has completed and all return values have been processed, `GirderFileId` will also remove the downloaded temporary file.


#### Handling function return values

The transforms as described so far provide a mechanism for getting Girder data onto the Girder Worker system and ultimately into the task function. A similar mechanism is used to handle task function return values.

_Note_ this represents a shift in expectations with regard to the legacy Girder Worker scripts. Previously scripts were responsible for assigning values to special variables which were plucked out of the executors namespace and processed. Modern Girder Worker tasks are designed to work with return values.

Consider the following task, which returns a path to an image on disk:

```python
from girder_worker.app import app
from matplotlib import pylab as plt

@app.task
def my_task(arg1, arg2):

	# Some analysis resulting in a matplotlib figure which is to be
	# saved to a temporary file stored in # output_path.

	plt.savefig(output_path)

    return output_path
```

The goal is to have the data stored at `output_path` uploaded to a Girder Item. For this purpose we will use `GirderUploadToItem` from Girder worker's utilities. To make sure the task calls this transform we must use a special keyword argument when launching the task. That argument is the `girder_result_hooks`:

```python
from girder_worker_utils.transforms.girder_io import GirderUploadToItem
from my_package.tasks import my_task

# Some code that determines then item_id to upload the result too.

my_task.delay(arg1, arg2,
    girder_result_hooks=[
		GirderUploadToItem(item_id),
	])
```

Note that `girder_result_hooks` takes a sequence. Should a task function return a tuple of arguments, each argument will be passed to the result transform object in the sequence. E.g.:

```python
my_task.delay(arg1, arg2,
    girder_result_hooks=[
		GirderUploadToItem(item_id), # results[0]
		GirderUploadToItem(item_id), # results[1]
		# ....                       # results[...]
	])
```

This provides a generic mechanism to handle side effects on the results of a task function at the time the task is launched.

#### Creating your own transforms

While the Girder worker utilities provide some pre-defined transforms, it is expected that most applications will need to write their own more specialized transforms.

Actual transform classes are derived from the [girder\_worker\_utils.transform.Transform](https://github.com/girder/girder_worker_utils/blob/master/girder_worker_utils/transform.py#L6-L26) abstract base class. This class defines a simple API which includes the `transform` and `cleanup` methods:

```python
@six.add_metaclass(abc.ABCMeta)
class Transform(object):
    def __init__(self, *args, **kwargs):
        pass

    def cleanup(self):
        pass

    @abc.abstractmethod
    def transform(self):
        pass
```

Now consider following implementation of the `GirderFileId` transform:

```python
import shutil
from girder_worker_utils.transforms.girder_io import GirderClientTransform

class GirderFileId(GirderClientTransform):
    def __init__(self, _id, **kwargs):
        super(GirderFileId, self).__init__(**kwargs)
        self.file_id = _id

    def transform(self):
        self.file_path = os.path.join(
            tempfile.mkdtemp(), '{}'.format(self.file_id))

        self.gc.downloadFile(self.file_id, self.file_path)

        return self.file_path

    def cleanup(self):
        shutil.rmtree(os.path.dirname(self.file_path),
                      ignore_errors=True)
```

Note that the `transform` method will be called before the task execution begins, and here will download the file with the `GirderClient.downloadFile` method. The `cleanup` method will be called after the task execution ends. 

_Note_ that this transform inherits from [girder\_worker\_utils.transforms.girder_io.GirderClientTransform](https://github.com/girder/girder_worker_utils/blob/master/girder_worker_utils/transforms/girder_io.py#L10-L22), which provides a `gc` attribute on the transform. `self.gc` will be a fully functional `GirderClient` available inside the `transform(...)` function.

##### Creating your own result transforms

Transforms of task function return values are derived from the `girder_worker_utils.transform.ResultTransform` abstract base class.

Now, consider the following result transform:

```python
from girder_worker_utils.transforms.girder_io import GirderClientResultTransform

class GirderUploadToItem(GirderClientResultTransform):
    def __init__(self, _id, **kwargs):
        super(GirderUploadToItem, self).__init__(**kwargs)
        self.item_id = _id

    def transform(self, data):
        self.gc.uploadFileToItem(self.item_id, data)
        return self.item_id
```

Unlike the `Transform` class, classes derived from `ResultTransform` expect a value to be passed to the `transform()` method. In the case of a task function that returns a single value, this value is the return value of the task function. In the case of a task function that returns a tuple of values, this will be one of the positional return values. In the `GirderUploadToItem` transform we take the data and pass it on to the `GirderClient.uploadFileToItem` function.

_Note_ It is best practice to return a meaningful value from a `ResultTransform.transform()` function. That value will be forwarded on to the Celery results back end, and used in subsequent tasks in the case of Celery task chaining.


### FAQ

1. [What if my task has complex install dependencies?](HACKING.md#what-if-my-task-has-complex-install-dependencies)

2. [How do I write a custom Celery task from scratch (e.g. without the cookiecutter)](HACKING.md#how-do-i-write-a-custom-celery-task-for-girder-worker). A related question: What is the cookiecutter actually doing?

3. What about Girder I/O? How do I push and pull data?
  Please use Transforms to manage this process. The base Transform class is implemented in girder\_worker\_utils.transform.Transform. Currently there are several example implementations of transforms in girder\_worker\_utils.transforms.girder_io. We are hoping that as more projects implement common useful Transforms that these will be upstreamed into girder\_worker\_utils.

## "Docker" Mode Legacy Tasks
TODO

## "Other" Mode Tasks
Girder Worker no longer explicitly supports tasks written in other modes (e.g. R, scala, etc). Custom tasks could be written to support these modes based on the legacy executor.py file that implements that mode. For more information please [contact the Girder Worker developers via our Gitter chat](https://gitter.im/girder/girder_worker).
