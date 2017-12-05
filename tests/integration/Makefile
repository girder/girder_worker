.DEFAULT_GOAL := initialize

COMPOSE_FILE=docker-compose.yml
COMPOSE_LOGS_EXTRA_ARGS=

initialize:
	pip install -U -r requirements.txt

dev:
	$(eval COMPOSE_FILE=docker-compose.dev.yml)
	$(eval COMPOSE_LOGS_EXTRA_ARGS="--tail=15")

init:
	docker-compose -f $(COMPOSE_FILE) up -d
	-docker-compose -f $(COMPOSE_FILE) exec girder /scripts/wait-for-it.sh localhost:8989 -t 60
	docker-compose -f $(COMPOSE_FILE) logs $(COMPOSE_LOGS_EXTRA_ARGS) girder
	docker-compose -f $(COMPOSE_FILE) logs $(COMPOSE_LOGS_EXTRA_ARGS) girder_worker


clean:
	docker-compose -f $(COMPOSE_FILE) stop
	docker-compose -f $(COMPOSE_FILE) rm -vf
	-docker rmi -f integration_girder_worker_data_volume

nuke: clean
	-docker rmi \
	  girder/girder:gw_integration_test \
	  girder/girder_worker:gw_integration_test

test-ci:
	-docker run --volumes-from girder_worker_data_volume \
                   --network container:gw_integration_test_girder \
          python:2.7.13 \
          /bin/bash -c "cd /girder_worker/tests/integration && make && make test"

test:
	pytest -v -x -n4


.PHONY: initialize dev ci clean nuke test
