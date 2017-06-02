#!/bin/bash

# If /girder_worker/setup.py exists then we've
# mounted girder_worker at run time,  make sure it
# is properly installed before continuing
if [ -e /girder_worker/setup.py ]; then
    pip install -e /girder_worker
fi

# If /girder_worker/setup.py exists then we've
# mounted girder_worker at run time,  make sure it
# is properly installed before continuing
if [ -e /girder_worker/tests/integration/common_tasks/setup.py ]; then
    pip install -e /girder_worker/tests/integration/common_tasks/
fi


# Start up Girder in the background
(python -m girder "$@" > girder_entrypoint.log 2>&1) &

# Wait for it to be done starting
until grep -qi 'engine bus started' girder_entrypoint.log; do sleep 1; done;


# Provision the running instance of girder
pushd /scripts
ansible-playbook -i inventory setup.yml
popd


# Tear down Girder
kill $(pgrep -f girder)

# Start Girder for the container process
python -m girder "$@"
