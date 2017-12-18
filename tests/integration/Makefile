.DEFAULT_GOAL := initialize

COMPOSE_FILE=docker-compose.yml
ANSIBLE_INVENTORY=inventory
ANSIBLE_EXTRA_VARS=-e girder_host=girder -e girder_port=8989 -e celery_broker="amqp://guest:guest@rabbit/"

initialize:
	pip install -U -r requirements.txt
	ansible-galaxy install --force --roles-path ./scripts/roles girder.girder

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

test:
	pytest -v -x -n4  -m 'not docker'


.PHONY: initialize dev clean nuke test init run
