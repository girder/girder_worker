#!/bin/bash

RABBITMQ_USER=${RABBITMQ_USER:-guest} \
RABBITMQ_PASS=${RABBITMQ_PASS:-guest} \
RABBITMQ_HOST=${RABBITMQ_HOST:-localhost} \
celery -A girder_worker.app worker -l INFO $@