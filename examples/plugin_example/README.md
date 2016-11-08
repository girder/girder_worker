# Girder Worker Example Plugin

This is an example plugin that demonstrates how to extend girder\_worker by allowing it to run additional tasks. Plugin's are implemented as separate pip installable packages.  To install this example plugin you can checkout this code base,  change directories to ```examples/plugin_example/``` and run ```pip install .```  This will add the ```gwexample``` plugin to girder\_worker.  If you then run girder\_worker with a log level of 'info' (e.g.  ```girder-worker -l info```)  you should see the following output:

```
(girder)kotfic@minastirith:~/kitware/projects/src/girder_worker ⇒ girder-worker -l info
 
 -------------- celery@minastirith v3.1.23 (Cipater)
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
[2016-11-08 12:22:57,218: WARNING/MainProcess] celery@minastirith ready.
```


Notice that the task ```gwexample.analyses.tasks.fibonacci``` is now available. With the girder-worker worker running,  you should be able to execute ```python example_client.py``` in the current working directory.  After a brief delay, this should print out ```121393``` - the Fibonacci number for 26. 

## Writing your own plugin

Adding additional tasks to the girder\_worker infrastructure is easy and takes three steps. (1) Creating tasks,  (2) creating a plugin class and (3) adding a ```girder_worker_plugins``` entry point to your setup.py.

### Creating tasks

Creating tasks follows the standard [celery conventions](http://docs.celeryproject.org/en/latest/userguide/tasks.html). The only difference is the celery application that decorates the function should be imported from ```girder_worker.app```. E.g.:

```python
from girder_worker.app import app

@app.task
def fibonacci(n):
    if n == 1 or n == 2:
        return 1
    return fibonacci(n-1) + fibonacci(n-2)

```
### Plugin Class

Each plugin must define a plugin class the inherits from ```girder_worker.GirderWorkerPluginABC```. GirderWorkerPluginABC's interface is simple.  The class must define an ```__init__``` function and a ```task_imports``` function.  ```__init__``` takes the girder\_worker's celery application as its first argument.  This allows the plugin to store a reference to the application,  or change configurations of the application as necessary. The ```task_imports``` function takes no arguments and must return a list of the package paths (e.g. importable strings) that contain the plugin's tasks. As an example:

```python
from girder_worker import GirderWorkerPluginABC

class GWExamplePlugin(GirderWorkerPluginABC):
    def __init__(self, app, *args, **kwargs):
        self.app = app

        # Update the celery application's configuration
		# it is not necessary to change the application configuration
		# this is simply included to illustrate that it is possible. 
        self.app.config.update({
            'TASK_TIME_LIMIT': 300
        })

    def task_imports(self):
        return ['gwexample.analyses.tasks']

```

### Entry Point

Finally,  in order to make the plugin class discoverable,  each plugin must define a custom entry point in its ```setup.py```. For our example,  this entry point looks like this:

```python
from setuptools import setup

setup(name='gwexample',
	  # ....
      entry_points={
          'girder_worker_plugins': [
              'gwexample = gwexample:GWExamplePlugin',
          ]
      },
      # ....
	  )
```

Python [Entry Poitns](https://setuptools.readthedocs.io/en/latest/pkg_resources.html#entry-points) are a way for python packages to advertise classes and objects to other installed packages.  Entry points are defined in the following way:

```python
	entry_points={
		'entry_point_group_id': [
			'entry_point_name = importable.package.name:class_or_object',
		]
	}
```

The girder_worker package introduces a new entry point group ```girder_worker_plugins```. This is followed by a list of strings which are parsed by setuptools.  The strings must be in the form  ```name = module:plugin_class```  Where ```name``` is an arbitrary string (by convention the name of the plugin),  ```module``` is the importable path to the module containing the plugin class,  and ```plugin_class``` is a class that inherits from ```GirderWorkerPluginABC```.


## Final notes
With these three components (Tasks, Plugin Class, Entry Point) you should be able to add arbitrary tasks to the girder_worker client.  By default,  jobs created in girder using the 'worker' plugin run the ```girder_worker.run``` task. This can be overridden to call custom plugin tasks by generating jobs with a ```celeryTaskName``` defined in the job's ```otherFields``` key word argument.  E.g.:

```python

# Create a job to be handled by the worker plugin
job = jobModel.createJob(
    title='Some Job', type='some_type', handler='worker_handler',
    user=self.admin, public=False, args=(25), kwargs={},
    otherFields={
        'celeryTaskName': 'gwexample.analyses.tasks.fibonacci'
    })

jobModel.scheduleJob(job)
```

This will schedule a job that runs ```gwexample.analyses.tasks.fibonacci(25)``` on the girder worker. 

Finally,  by default the core girder\_worker tasks (```run```, ```convert```, ```validate```) are included along with their plugins etc. If you wish to prevent these tasks from being loaded inside the celery instance, you can configure ```core_tasks=false``` in ```worker.local.cfg``` under the  ```[girder_worker]``` section of the configuration.



