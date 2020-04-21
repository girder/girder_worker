*Note: This documentation is a work in progress, if you find problems with it's construction or it's content. Please file an issue!*

# What is this all about?
In this documentation we will descend through increasingly detailed descriptions of Girder Worker and its relationship to [Celery](http://www.celeryproject.org/), ending up with descriptions of how you can use Girder Worker to run remote asynchronous tasks.

## 10,000 foot view
Girder Worker is an application that wraps Celery; it relies on Celery's distributed task execution mechanisms to do work, while reflecting task state and logging information back into [Girder](https://girder.readthedocs.io/) for visualization, debugging and management. Girder Worker is designed to receive and execute tasks that have been produced by Girder. Messages that encode what tasks and task arguments are passed from Girder to Girder Worker via a separate service called a [broker](http://docs.celeryproject.org/en/latest/getting-started/brokers/). In many common setups this broker is [RabbitMQ](https://www.rabbitmq.com/).

Girder Worker runs in a separate process from Girder. It may run on the same physical machine as Girder, or may be run on one or more separate machines. At a low level, RabbitMQ brokers the communication between Girder and Girder Worker. If Girder and Girder Worker are running on separate machines, both machines must be able to connect to the server running RabbitMQ.

Girder Worker's configuration is managed by an INI style configuration file located in `girder_worker/worker.dist.cfg`. This file is version controlled and should not be directly modified. To customize configurations copy the `worker.dist.cfg` to `worker.local.cfg` and make your modifications there. There are several commented configurations available in the configuration file. The most important is the `broker` config under the `[celery]` section. This is how Girder Worker connects to RabbitMQ and should follow Celery's [broker_url](http://docs.celeryproject.org/en/latest/userguide/configuration.html#broker-url) syntax.

Assuming you have configured Girder Worker to connect to the RabbitMQ service, running Girder Worker is easy. From a command line simply run:

```sh
$> girder-worker
```

Or if you are using [systemd](https://www.freedesktop.org/wiki/Software/systemd/) you may create a simple service file:

```sh
[Unit]
Description=Girder Worker Service
After=network.target

[Service]
Type=simple
User=GIRDER_USER
Group=GIRDER_GROUP

ExecStart=/path/to/girder-worker
ExecStop=/path/to/bin/celery multi stopwait worker

[Install]
WantedBy=multi-user.target
```
Replace `GIRDER_USER` and `GIRDER_GROUP` with the user and group you want the service to run as. Save the file as `/etc/systemd/system/girder_worker.service` and run `sudo systemctl daemon-reload`. Finally execute `systemctl start girder_worker` to run the girder_worker service.

### Vocabulary

Vocabulary can be an area of confusion when dealing with these systems. In an attempt to be clear we will draw a strong, jargon-like, distinction between the terms *Job* and *Task*.

The term **Job** will always refer to the concept of a Girder [Job](http://girder.readthedocs.io/en/latest/plugins.html#jobs). Jobs are displayed on the Job's panel in Girder. They are represented in the database as [Job Models](https://github.com/girder/girder/blob/master/plugins/jobs/server/models/job.py). Girder Job's have various states and notification streams, and can be scheduled to execute on Girder Worker.

The term **Task** on the other hand will always refer to the Celery concept of a [Task](http://docs.celeryproject.org/en/latest/userguide/tasks.html). Tasks are typified by decorated Python functions that can be scheduled to run on Girder Worker via the Celery [task calling api](http://docs.celeryproject.org/en/latest/userguide/calling.html). Unlike Jobs, Tasks are not stored in a database. Tasks are Python functions, defined in a Python module, that have been decorated by the Girder Worker's `@app.task` decorator. This means they do not exist until they are imported from the module in which they are defined.

Related to tasks are [messages](http://docs.celeryproject.org/en/latest/internals/protocol.html). A **Message** is the serialized task object that is placed on a broker's queue. By default, serialization is achieved by creating a dictionary of the function name, the arguments, keyword arguments and message metadata and then serializing this dictionary as a JSON string. Commonly message serialization and queuing happens on the Girder side, this is called *producing* a message, and in this case you might describe Girder as a **Producer** (Note that it is possible for other things to produce messages including Girder Worker. An example of when this would happen is using celery's [canvas](http://docs.celeryproject.org/en/latest/userguide/canvas.html) features). In our case, Girder Worker usually pulls messages off of the queue, deserializes them back into Celery Task objects and then applies those task objects to the arguments and keyword arguments encoded in the message. This is referred to as *consuming* a message and makes Girder Worker a **Consumer**.

To Recap:

+ **Job** - The Girder model that provides UI for the Celery Task
+ **Task** - The Celery object that wraps a developer defined function
+ **Message** - A serialized Task object and its arguments
+ **Producer** - Anything that generates a message with its arguments and places it on the queue.
+ **Consumer** - Anything that dequeues a message, deserializes it into a Task object and applies that object to the message arguments.

## 1,000 foot view

There are currently two approaches of using Girder to produce messages for consumption by Girder Worker.

### The traditional approach

The first, called the "traditional" approach is to use the [Worker](http://girder.readthedocs.io/en/latest/plugins.html#remote-worker) plugin to create and schedule a Girder job. The worker job handler then produces a celery message and places it on the queue for consumption by Girder Worker. This is a *Job creates Task* approach (though more accurately it is *Job creates message, which is consumed by Girder Worker, where the message is applied to as Task*).

The traditional approach is historically how Girder Worker was used going all the way back to its progenitor [Romanesco](https://github.com/Kitware/romanesco). It is consistent Girder's approach to Jobs; it attempts to abstract the notion of a job from the mechanism that schedules that job. For simple cases this is sufficient but it limits the power of individual schedulers to the common semantics of the Job.

### The Celery approach
The second (and preferred) approach is the Celery approach. In this approach a celery task object is imported from a package and called using the standard celery API (e.g. with the `.delay(...)` or the `.apply_async(...)` methods). As long as the task object inherits from custom task class `girder_worker.app.Task` then this approach will create a Girder Job automatically. This is a *Task creates Job* approach.

## An Example Task
To illustrate the differences between the traditional and Celery approaches of executing remote tasks, we'll use an example task `fibonacci` that inefficiently calculates the [Fibonacci number](https://en.wikipedia.org/wiki/Fibonacci_number) of an input parameter `n`:

```python
from girder_worker.app import app

@app.task
def fibonacci(n, **kwargs):
    if n == 1 or n == 2:
        return 1
    return fibonacci(n-1) + fibonacci(n-2)
```

Tasks such as this must be placed in a package that is Python importable. For our purposes we will assume this task can be imported from `my_custom_package.tasks`

For Example:
```python
from my_custom_package.tasks import fibonacci
```

*Note that in various girder_worker tests, we use an inefficient implementation of `fibonacci` because it nicely simulates a long running, computationally intensive, function.*

### The traditional approach

To run the `fibonacci` task remotely through Girder Worker using the traditional approach, we must create a Girder job, save that job, and schedule it using the Worker plugin. To produce a Celery message using the traditional approach, two conditions must be met:
  1. the Worker plugin must be enabled from the admin plugins panel and
  2. the `handler` key word argument must be set to the string `worker_handler` in the `createJob(...)` function.

The following code illustrates how to create, save, and schedule the fibonacci job:

```python
from girder.plugins.jobs.models.job import Job

# Create the job
job = Job.createJob(
    title='<NAME OF THE JOB>',
    type='<JOB TYPE>',
    handler='worker_handler',
    user=getCurrentUser(),
    public=False,
    args=(20,),
    kwargs={},
    otherFields={
        'celeryTaskName': 'my_custom_package.tasks.fibonacci'
    })

# Save the job
Job.save(job)

# Schedule the job
Job.scheduleJob(job)
```

*This is code you might see in a REST request handler that is dedicated to launching fibonacci jobs. See the [Jobs](http://girder.readthedocs.io/en/latest/plugins.html?highlight=schedule#jobs) documentation for more information about creating, saving and scheduling jobs.*

The params of the job model singleton `createJob` are:
+ `title` which sets the display title of the Job
+ `type` which sets the Job type (Note that `type` is a arbitrary string used to categorize jobs, it has no behavior)
+ `user` which should be an instance of a user model; the job will belong to this user
+ `public` which affects whether or not anonymous users can see the job or not
+ `args` which is a list of arguments to apply the consumer-side task object to (In our example `n` in `my_custom_package.tasks.fibonacci` will be `20`)
+ `kwargs` which is a list of keyword arguments to which the consumer-side task object is applied (in our example there are none)
+ `handler` which *must be* `"worker_handler"`, or the Worker plugin handler will not execute and the Celery message will not be produced
+ `otherFields` which is a dictionary of fields that are specific to Worker plugin job models

Currently the Worker plugin supports two `otherFields`:

+ `celeryTaskName` should be the name of the task object. This is almost always the Python importable path to the task as a string (unless you have specifically set the [name](http://docs.celeryproject.org/en/latest/userguide/tasks.html#names) when decorating the function). In our example this is the string `"my_custom_package.tasks.fibonacci"`. If you do not specify a `celeryTaskName` in `otherFields` it will use "girder_worker.run" by default.
+ `celeryQueue` allows you to place the produced message on a different RabbitMQ queue than the default `celery` queue.

For the final part of our example we use the jobModel singleton to save the job to the database and then schedule the job to execute.

#### Notes about the traditional approach

In general the traditional approach is not the preferred approach for producing tasks from Girder. As we will see, it takes several additional steps compared to the Celery approach. More importantly, the traditional approach can ***only*** use the default Celery [configurations](http://docs.celeryproject.org/en/latest/userguide/configuration.html), with the exception of the backend and broker settings (for why, see "Issues with the traditional approach" under the architectural notes section).

The one advantage of the traditional approach is that it does not require the package that defines your task objects to be installed in the Producer's environment (e.g. `my_custom_package` in our example does not have to be installed on the same server as Girder). This can be helpful if for some reason you do not have deploy time control over the Girder environment, or if you have a particularly difficult set of dependencies that would need to be installed in both the Girder and Girder Worker Python environments (though, see: "What if my task has complex install dependencies?" for suggestions on how to mitigate this issue with the Celery approach).


## The Celery approach

The Celery approach for producing messages from Girder to be consumed by Girder Worker is the preferred approach. This requires installing the package that contains the task (e.g. `my_custom_package`) in the girder environment. Once this is complete the following code will produce (generate and enqueue) a message and, as a side-effect, it will create a Girder Job.

```python
# Import the Celery Task object
from my_custom_package.tasks import fibonacci

# Generate a message and place it on the queue
async_result = fibonacci.delay(20)

# Return the Girder Job
return async_result.job
```

*Note that, like the code for the traditional approach, this is code you might see in a REST request handler that is dedicated to launching `fibonacci` jobs. See the [Celery Task API](http://docs.celeryproject.org/en/latest/userguide/calling.html) for more information about how to call and configure celery tasks.*

The previous code should look familiar to anyone who has used a Celery task before. We import the `fibonacci` task object from the `my_custom_package.tasks` module and then call `.delay(20)`. This will generate a message and consumer-side will apply the fibonacci function to the number 20 (returning 6765). The only surprising part should be referencing `async_result.job`. Girder Worker tasks inherit from a custom base task. This base task creates the Girder Job and returns a subclassed version of `celery.result.AsyncResult` that includes a `job` property. This `job` attribute will return the Girder Job model that was created as a side effect of generating and en-queuing the message.


### Notes about the Celery approach

While the Celery approach is much more terse than the traditional approach, the astute reader will recognize that it does not (as illustrated) provide the ability to modify the properties of the Girder Job that is generated. In fact, using the fibonacci task introduced previously, with the Celery approach will produce a job in the Girder Job panel with the title "\<unnammed job\>". To remedy this situation a series of reserved Girder Worker specific keywords may be passed to any of the Celery Task API methods. These keywords allow per-task invocation modification of the generated Girder Job. They are:

+ **girder_job_title** This changes the job title, by default (e.g if `girder\_job\_title` is omitted) it is `"\<unnamed job\>"`.
+ **girder_job_type** This changes the job type, by default it is `"celery"` (Note that `girder_job_type` is a arbitrary string used to categorize jobs, it has no behavior).
+ **girder_job_public** This changes the public status of the job, by default it is `False`.
+ **girder_job_handler** This changes the job handler, by default it is `"celery_handler"` (Note: do not change this unless you are sure you know what you are doing).
+ **girder_job_other_fields** This field allows you to set additional handler specific fields on the Job. Currently the "celery_handler" has no additional standard fields. This could however be used to extend the job model data to suit application specific needs.  The `"meta"` field is displayed by the Girder Jobs plugin as part of the job details.
+ **girder_user** This field sets the girder user which belongs to the job. It should be a full user model. By default it is the return value of `girder.api.rest.getCurrentUser()`

Here is an example of using these fields:

```python
# Import the Celery Task object
from my_custom_package.tasks import fibonacci

# Generate a message and place it on the queue
async_result = fibonacci.delay(20,
	girder_job_title='Fibonacci Job',
	girder_job_type='my_custom_type',
	girder_job_public=True,
	girder_job_other_fields= {
		'some_custom_field': 'some_custom_value'
	})

# Return the Girder Job
return async_result.job
```

These keyword arguments may also be passed to the `.apply_async(...)`, `.s(...)` and `.signature(...)` methods:

```python
async_result = fibonacci.apply_async(
	args=(20,),
	kwargs={},
	girder_job_title='Fibonacci Job',
	girder_job_type='my_custom_type',
	girder_job_public=True,
	girder_job_other_fields= {
		'some_custom_field': 'some_custom_value'
	})
```

Or equally:

```python
sig = fibonacci.s(20,
	girder_job_title='Fibonacci Job',
	girder_job_type='my_custom_type',
	girder_job_public=True,
	girder_job_other_fields= {
		'some_custom_field': 'some_custom_value'
	})

async_result = sig.delay()

return async_result.job
```


#### Job Defaults

The above keyword arguments can be used to set per-invocation values for the generated job model. While this is useful for specific invocations, generally Girder Job metadata will be similar across task invocations. Default values for this metadata may be set by decorating the task definition with the `girder_job` decorator:

```python
from girder_worker.utils import girder_job
from girder_worker.app import app


@girder_job(title='Fibonacci Job',
	type='my_custom_type',
	public=True, otherFields={
	'some_custom_field': 'some_custom_value'})
@app.task
def fibonacci(n, **kwargs):
	if n == 1 or n == 2:
		return 1
	return fibonacci(n-1) + fibonacci(n-2)

```

Decorated like so, the `fibonacci.delay(...)` function will act as though the corresponding keyword arguments were passed into the function. Defaults defined with `@girder_job` will be over-ridden by invocation specific keyword arguments. Note that the `girder_job` decorator must be placed *after* the `app.task` decorator.

#### Girder Client
Each task that is running consumer-side has access to a Girder Client object for talking back to the deployment of Girder that spawned that task. By default this client has the permissions of an unauthenticated user and expects Girder to be running at localhost on port 8080. This can be changed by using the following reserved keyword arguments:

+ **girder_client_token**
+ **girder_api_url**

These are **not** used in Girder job creation, but instead provide each executing consumer-side task with access to an instantiated [GirderClient](http://girder.readthedocs.io/en/latest/python-client.html#the-python-client-library). This client can be used to perform arbitrary RESTful calls against the girder deployment. The URL location of the girder API is specified with `girder_api_url` keyword argument. The default `girder_api_url` will be the return value of `girder.plugins.worker.utils.getWorkerApiUrl()`. The client will be instantiated with the `girder_client_token` as its authentication mechanism. This means the consumer-side client will have permissions that are consistent with the scopes applied to the token. The default `girder_client_token` is `None`.

An example:

Producer side REST endpoint:
```python
from my_custom_module.tasks import some_task
from girder.models.token import Token

...

@access.token
@filtermodel(model='job', plugin='jobs')
@describeRoute(
	Description('Launch a task, making a scoped token available to the girder_client in the task.')
	.param('file_id', 'File Id to run "some_task" on', dataType='string'))
def some_rest_endpoint(file_id, **params):
	# Create a token with permissions of the current user.
	token = Token().createToken(
		user=self.getCurrentUser())

	# Launch the asynchronous task
	async_result = some_task.delay(file_id, girder_client_token=token['_id'])

	return async_result.job
```

Consumer side task:
```python
from girder_worker.app import app

@app.task(bind=True)
def some_task(self, file_id):
	# Note: girder_client is available as an attribute of 'self'
	# self (the task object) will be passed to the function if
	# bind is set to True in the task decorator.
	self.girder_client.downloadFile(file_id, '/tmp/file')
	with open('/tmp/file', 'rb') as f:
		# Do something with contents of f
```

In this example the producer side REST endpoint creates a token with the scope of the current user, then passes the REST argument `file_id` and the token to the task object's `.delay(...)` function. On the consumer side, the task has access to the GirderClient instance through `self.girder_client`. To get access to `self` the task must be decorated with `@app.task(bind=True)` (See [bound tasks](http://docs.celeryproject.org/en/latest/userguide/tasks.html#bound-tasks) for more information).

# How do I write a custom Celery task for Girder Worker?

*Note that this is taken almost directly from [Writing your own plugin](http://girder-worker.readthedocs.io/en/latest/developer-docs.html#writing-your-own-plugin)*

Adding additional tasks to the girder\_worker infrastructure takes three steps.

1. Creating tasks in a Python package
2. Creating a plugin class that informs Girder Worker there are tasks in the Python package
3. Adding a girder\_worker\_plugins [entry point](http://setuptools.readthedocs.io/en/latest/setuptools.html#dynamic-discovery-of-services-and-plugins) to your setup.py.

Creating tasks follows the [standard celery conventions](http://docs.celeryproject.org/en/latest/userguide/tasks.html#basics). The only difference is the celery application that decorates the function should be imported from girder_worker.app. E.g.:

```python
from girder_worker.app import app

@app.task
def fibonacci(n, **kwargs):
	if n == 1 or n == 2:
		return 1
	return fibonacci(n-1) + fibonacci(n-2)

```

As before, we'll assume that this function is defined in the `tasks` module of `my_custom_package`. Each plugin must define a plugin class the inherits from `girder_worker.GirderWorkerPluginABC`. `GirderWorkerPluginABC` is an abstract base class with a simple interface that must be implemented by it's subclasses. The class must define an `__init__` function and a `task_imports` function. `__init__` takes the `girder_worker`'s celery application as its first argument. This allows the plugin to store a reference to the application, or change configurations of the application as necessary. The `task_imports` function takes no arguments and must return a list of the package paths (e.g. importable strings) that contain the plugin’s tasks. As an example:

```python
from girder_worker import GirderWorkerPluginABC

class MyCustomPackagePlugin(GirderWorkerPluginABC):
    def __init__(self, app, *args, **kwargs):
        self.app = app

        # Update the celery application's configuration
        # it is not necessary to change the application configuration
        # this is simply included to illustrate that it is possible.
        self.app.config.update({
            'TASK_TIME_LIMIT': 300
        })

    def task_imports(self):
        return ['my_custom_package.tasks']
		
```

Setuptools entry points are a way for Python packages to advertise classes and objects to other installed packages. In order to make the plugin class discoverable by Girder Worker, each plugin must define a custom entry point in its setup.py. For our example, this entry point looks like this:

```python
from setuptools import setup

setup(name='gwexample',
      # ....
      entry_points={
          'girder_worker_plugins': [
              'my_custom_package = my_custom_package:MyCustomPackagePlugin',
          ]
      },
      # ....
      )
```

The `girder_worker` package introduces a new entry point `girder_worker_plugins`. This is followed by a list of strings which are parsed by setuptools at install time. The strings must be in the form `name = module:plugin_class`, where `name` is an arbitrary string (by convention the name of the plugin), `module` is the importable path to the module containing the plugin class, and `plugin_class` is a class that inherits from `GirderWorkerPluginABC`.

For more on entry points, see the [setuptools documentation](http://setuptools.readthedocs.io/en/latest/setuptools.html#dynamic-discovery-of-services-and-plugins).

Once you have defined your tasks, created a plugin class, setup your entrypoint, and installed your package, you can verify that your task is being properly discovered by running

```sh
$> girder-worker -l info
```

This should provide a list of discovered tasks under `[tasks]`:

```sh
(girder)$> girder-worker -l info

 -------------- celery@host v4.0.2
---- **** -----
--- * ***  * -- Linux-4.8.6-1-ARCH-x86_64-with-glibc2.2.5
-- * - **** ---
- ** ---------- [config]
- ** ---------- .> app:         girder_worker:0x7f69bfff1050
- ** ---------- .> transport:   amqp://guest:**@localhost:5672//
- ** ---------- .> results:     amqp://
- *** --- * --- .> concurrency: 32 (prefork)
-- ******* ----
--- ***** ----- [queues]
 -------------- .> celery           exchange=celery(direct) key=celery


[tasks]
  . girder_worker.convert
  . girder_worker.run
  . girder_worker.validators
  . gwexample.analyses.tasks.fibonacci

[2016-11-08 12:22:56,163: INFO/MainProcess] Connected to amqp://guest:**@127.0.0.1:5672//
[2016-11-08 12:22:56,184: INFO/MainProcess] mingle: searching for neighbors
[2016-11-08 12:22:57,198: INFO/MainProcess] mingle: all alone
[2016-11-08 12:22:57,218: WARNING/MainProcess] celery@host ready.
```


## What if my task has complex install dependencies?

One of the few disadvantages of the Celery approach is requiring that the package that contains your task be installed on both the consumer (where the task is run) and the producer (where the task is enqueued). Normally this isn't a big problem, especially if your tasks are only using functions from Python's standard library.

In some cases however, tasks have complex dependencies that are difficult to install and it may be burdensome to install them in the producer (Girder) environment. Luckily this issue can be easily ameliorated by guarding imports in your task packages:

```python
from girder_worker.app import app

try:
	from complex_dependency import complex_function
except ImportError:
	pass

@app.task
def some_task(*args, **kwargs):
	return complex_function(*args, **kwargs)
```

Producer-side code will still generate the task objects, allowing them to produce task messages, while consumer-side code (where the `complex_dependency` package must be installed) will be able to execute the task body.

You may additionally wish to configure setuptools using [extras_require](http://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies) to manage the different between producer and consumer dependencies:

```python
setup(
	name="my_custom_package",

	install_requires=[
		"girder_worker",
		....
	],
	extras_require={
		'consumer':  ["complex_dependency", ...],
	}
	...
)
```

This means the producer side code can be installed with pip as `my_custom_package` and the consumer side code (that includes the complex dependencies) can be installed as `my_custom_package[consumer]`

## Communicating with Girder from inside Tasks

Tasks decorated with the Girder Worker application object have two main channels of interacting with the Girder deployment that produced the task.

The first is the `job_manager` which provides an API for interacting with the specific Girder job model that is reflecting the state of Celery Task. The job_manger is an instance of `girder_worker.utils.JobManager`. The `job_manager` is available on the task object, which means you must decorate the task with `bind` equal to `True` in order to access the job_manager (e.g. `@app.task(bind=true)`). This means the first argument to the task will be `self` and the `job_manger` will be available as `self.job_manager`. For the most part, task state transition is handled seamlessly through Girder Worker's use of [Celery Signals](http://docs.celeryproject.org/en/latest/userguide/signals.html). This means basic Job state transition (e.g. running, success, failure, retry, etc) will be handled without any intervention within the task. If you wish to use custom Job states, update the Job progress, or to log specific information to the Job from within your task, you can do so using the this `job_manager`. The `job_manager` is automatically generated regardless of whether you use the traditional approach or the Celery approach of producing your task. The `job_manager` is scoped so that it only has push access to the specific job it is assigned. If your task needs to leverage other components of the Girder REST API, including pushing data back to Girder or modifying Girder collections via the API, then you should use the `girder_client`.

The second channel for interacting with Girder from within a task is through the `girder_client` attribute. Like the `job_manager` it is available on the Celery task object (so you must set `bind` equal to `True` to access it). The `girder_client` is an instance of `girder_client.GirderClient`. It provides an authenticated session for making REST requests against the Girder API. The authentication is handled through a token provided to the task through the reserved keyword `girder_client_token`. This will allow the `girder_client` within the task to act with the same permissions granted to the token. If you have not set the `girder_client_token`, then by default it is `None`. This means the `girder_client` instance within the task will have the permissions of an unauthenticated user.


# Integration Testing with Girder Worker
TODO

# Architectural notes for Developers (and Masochists)

The following sections contain information about the implementation details of Girder Worker. They are not meant for general consumption, but may be useful in explaining some of the design decisions that were made for developers who wish to extend or contribute to Girder Worker.

## The 'core' plugin
TODO

## Celery Hooks and the reserved keywords
TODO

## The jobInfoSpec and the task job\_manager
TODO


## Issues with the traditional approach
When decorating a function and turning it into a task object, what you've really done is given the function two purposes in life. The first purpose is to execute the body of the function. The second purpose is to act as a factory for producing messages. When you use the traditional approach, you skip the factory entirely and just put a message on the queue using `app.send_task(...)`. This means task specific configuration that effects the message behavior between when you call a factory method `.delay(...)` and when you put the message on the queue is lost (for example rate limiting the message production). The fundamental issue with the traditional approach is how does one synchronize Celery's configuration across producer (Girder) and consumer (Girder Worker) processes, keeping in mind that these processes may be taking place on two (or more) different physical machines. Traditionally Celery solves this problem through the Python import mechanism. The Celery application is configured as a part of the Python package in which it is defined. By importing the application you get the same configuration on the producer as on the consumer. Assuming you are using the same version on both producer and consumer, then the application is imported consumer-side when running `girder-worker` and is imported implicitly producer-side when importing a Celery Task object (e.g. `from my_custom_package.tasks import fibonacci`).

The traditional approach does not use Celery Task objects to produce messages (e.g. with the `.delay(...)` or `.apply_async(...)` task methods). Instead it uses the `Celery.send_task(...)` method which is defined on the Celery application object. `.send_tasks(...)` is the lowest level API for producing messages in Celery. Rather than using a task object which is generated from a wrapped Python function it uses the task "name" (usually the string-ified importable path to the task). The advantage here is that the task does not need to be importable on the producer-side system, it doesn't even have to be installed at all. However, because the task object itself is not producing the message all producer-side task level configuration is lost when using `Celery.send_task(...)`. This might not be a deal-breaker except that the application object on the Girder producer-side is a *different application object* than on the Girder Worker consumer-side. The worker plugin does not import the `girder_worker.app` application object, instead it fabricates a new `Celery(...)` object before calling `.send_task(...)`. While on the one hand this means the `girder_worker` package doesn't need to be installed in the girder environment it *also* means that the Celery application object on the producer-side is a differently configured object then on the consumer-side. Celery has excellent defaults, and so maybe that isn't a problem for you and your use-case. If however, you need more sophisticated configurations than the defaults then currently the Celery approach for remote task execution is your only option.

### Note on using Python packages as synchronizing mechanism in Celery
Importable packages tightly bind code and configuration, which at first glance may seem bad. In fact this is critical because the configuration is fundamentally about how your code will be executed. Maintaining those in the same place reduces complexity and makes synchronization errors less likely. An importable package is also a pre-requisite for at least the consumer side of the equation (so the task can actually execute its function body). Importable packages prevent having to run a specific service to manage configuration, or sync configuration files across systems, they provide a versioned environment that ensures consistent interpretations of configuration values. Importable packages have strong tooling around their installation and deployment (pip) and once they are installed they have 100% up time.
