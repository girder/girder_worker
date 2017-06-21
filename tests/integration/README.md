# Girder Worker Integration Tests

This directory contains scripts and files necessary to run the girder worker integration tests. Integration tests are intended to provide end-to-end validation of the girder girder-worker system. To accomplish this we use several [docker containers](https://www.docker.com/what-container) to run the necessary services; one for girder, mongodb, girder worker and rabbitmq. We then use [pytest](https://docs.pytest.org/en/latest/contents.html) to run the actual integration tests which mostly make requests against girder's API to run jobs and make assertions about their status. 


Before running the tests you will need to make sure girder-worker is installed (either in a virtual environment,  or in your system's python environment).  To run the tests first


```
cd /path/to/girder_worker/tests/integration
docker-compose up
```

and run the tests:

```
cd /path/to/girder_worker/tests/integration
pip install -r requirements.txt
pytest -v
```

Test's may be sped up by paralleling their execution:

```
pytest -v -n 4
```

where ```4``` is the number of parallel test processes you wish to use. Please note that: _All tests should be written so that they can run in parallel_. This is critical for timely execution of the integration tests.



## Build the containers:
It is also to possible to build the containers locally.  You should be able to run:

```
cd /path/to/girder_worker/tests/integration
docker-compose build
```


