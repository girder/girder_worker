.DEFAULT_GOAL := initialize

COMPOSE_FILE=docker-compose.yml
ANSIBLE_INVENTORY=inventory
ANSIBLE_EXTRA_VARS=

initialize:
	pip install -U -r requirements.txt
	ansible-galaxy install --roles-path ./scripts/roles girder.girder

ci:
	$(eval COMPOSE_FILE=docker-compose.ci.yml)
	$(eval ANSIBLE_EXTRA_VARS=-e girder_host=girder -e girder_port=8989 -e celery_broker="amqp://guest:guest@rabbit/")
	$(eval ANSIBLE_INVENTORY=inventory.ci)

run:
	docker-compose -f $(COMPOSE_FILE) up -d
	cd scripts/ && ansible-playbook -i $(ANSIBLE_INVENTORY) $(ANSIBLE_EXTRA_VARS) setup.yml


worker_restart:
	docker-compose -f $(COMPOSE_FILE) restart girder_worker


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
                   --network container:gw_integration_test_girder_ci \
          python:2.7.13 \
          /bin/bash -c "cd /girder_worker/tests/integration && make && pytest --girder http://girder:8989/api/v1/ -v -x -n4"

test:
	pytest -v -x -n4


.PHONY: initialize dev ci clean nuke test init
