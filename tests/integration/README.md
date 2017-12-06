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

Girder worker's integration tests use a [Makefile](https://www.gnu.org/software/make/manual/make.html) to coordinate calls to [docker-compose](https://docs.docker.com/compose/) which orchistrates the docker containers,  and [Ansible](http://docs.ansible.com/) which manages runtime configuration of the girder/girder-worker system for use with the test suite. The targets are as follows:

+ ```initialize``` - Install the required packages to run the test infrastructure (e.g. pytest, ansible)
+ ```run``` - Run docker-compose to bring up the system,  then ansible to configure the girder/girder-worker
+ ```test``` - Run the python tests locally (you may also simply run ```pytest```)
+ ```clean``` - Stop the containers and remove them.
+ ```nuke``` - Run ```clean``` but also remove the built images (these will be recreated next time your run ```make run```)
+ ```worker_restart``` - Restart the worker docker container.  This is nessisary if you make chances to tasks in common_tasks/


