#!/bin/bash


# Start up Girder in the background
(python -m girder "$@" > entrypoint.log 2>&1) &

# Wait for it to be done starting
until grep -qi 'engine bus started' entrypoint.log; do sleep 1; done;


# Provision the running instance of girder
pushd /scripts
ansible-playbook -i inventory setup.yml
popd

# If /girder_worker/setup.py exists then we've
# mounted girder_worker at run time,  make sure it
# is properly installed before continuing
if [ -e /girder_worker/setup.py ]; then
    pip uninstall -y girder-worker
    pip install -e /girder_worker
fi

# Tear down Girder
kill $(pgrep -f girder)

# Start Girder for the container process
python -m girder "$@"
