#!/bin/bash

/usr/bin/env RABBITMQ_USER=${RABBITMQ_USER:-guest} \
             RABBITMQ_PASS=${RABBITMQ_PASS:-guest} \
             RABBITMQ_HOST=${RABBITMQ_HOST:-localhost} \
             python -m girder_worker
