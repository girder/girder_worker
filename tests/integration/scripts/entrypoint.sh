#!/bin/bash


# Start up Girder in the background
(python -m girder "$@" > entrypoint.log 2>&1) &

# Wait for it to be done starting
until grep -qi 'engine bus started' entrypoint.log; do sleep 1; done;


# Provision the running instance
pushd /scripts
ansible-playbook -i inventory setup.yml
popd

# Tear down Girder
kill $(pgrep -f girder)

# Start Girder for the container process
python -m girder "$@"
