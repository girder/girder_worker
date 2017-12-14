# Girder Worker Integration Tests

This directory contains scripts and files necessary to run the girder worker integration tests. Integration tests are intended to provide end-to-end validation of the girder girder-worker system. To accomplish this we use several [docker containers](https://www.docker.com/what-container) to run the necessary services; one for girder, mongodb, girder worker and rabbitmq. We then use [pytest](https://docs.pytest.org/en/latest/contents.html) to run the actual integration tests which mostly make requests against girder's API to run jobs and make assertions about their status. 


Before running the tests you will need to make sure girder-worker is installed (either in a virtual environment,  or in your system's python environment).  To run the tests first install the nessisary tools:


```
cd /path/to/girder_worker/tests/integration
make
```

Then run the system:
```
make run
```

and run the tests:

```
pytest -v
```

Test's may be sped up by paralleling their execution:

```
pytest -v -n 4
```

where ```4``` is the number of parallel test processes you wish to use. Please note that: _All tests should be written so that they can run in parallel_. This is critical for timely execution of the integration tests.

# Integration Test Make Targets

Girder worker's integration tests use a [Makefile](https://www.gnu.org/software/make/manual/make.html) to coordinate calls to [docker-compose](https://docs.docker.com/compose/) which orchestrates the docker containers,  and [Ansible](http://docs.ansible.com/) which manages run-time configuration of the girder/girder-worker system for use with the test suite. The targets are as follows:

+ ```initialize``` - Install the required packages to run the test infrastructure (e.g. pytest, ansible). This is also the default target (i.e. ```make``` will run this target)
+ ```run``` - Run docker-compose to bring up the system,  then ansible to configure the girder/girder-worker
+ ```test``` - Run the python tests locally (you may also simply run ```pytest``` from the tests/integration folder)
+ ```clean``` - Stop the containers and remove them.
+ ```nuke``` - Run ```clean``` but also remove the built images (these will be recreated next time your run ```make run```)
+ ```worker_restart``` - Restart the worker docker container.  This is necessary if you make chances to tasks in common_tasks/

The following make targets use the ```docker-compose.yml``` file,  which mounts the host girder\_worker code inside the docker container.  This means you should be able to edit test endpoints and test tasks without needing to rebuild the containers. (_Note_ that you will need to restart the worker container if you change any of the test tasks in common\_tasks/). 

# Integration Test CI

These integration tests are run on CircleCI 2.0  using Circle's docker infrastructure.  To support this a few components of the test infrastructure need to be tweaked to run correctly.  This is accomplished with an intermediate target ```ci```.  Each of the above make targets may be prefixed with the ci target (e.g.  ```make ci run``` and ```make ci test```). 

## Gory details
The primary difference between the local infrastructure framework and the CI infrastructure framework is that circle does not allow [bind mounting](https://docs.docker.com/engine/admin/volumes/bind-mounts/) host directories into containers.  This means the girder-worker code must be copied into a docker data volume container and mounted using '--volumes-from' flag. 

To manage the differences between running the test framework locally and on CI  we have two different docker-compose files.  ```docker-compose.yml``` manages the local framework (e.g. ```make run```)  while ```docker-compose.ci.yml``` manages the CI framework (e.g. ```make ci run```). 

Finally,  the ```pytest``` command that actually runs the tests on CI must be run inside a docker container (The dominant theme of CircleCI 2.0's docker builds is that everything must be done inside a container). To accomplish this we run a standard python 2.7.13 container,  mount the data volume with girder worker inside the python container, then from ```/girder_worker/tests/integration``` it runs ```make``` and ```pytest ...``` to run the test suite against the docker containers.




