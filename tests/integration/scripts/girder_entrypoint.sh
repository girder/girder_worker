#!/bin/bash

if [ -e /girder_worker/tests/integration/integration_test_endpoints ]; then
    girder-install plugin -s /girder_worker/tests/integration/integration_test_endpoints/
else
    echo "COULD NOT INSTALL INTEGRATION_TEST_ENDPOINTS"
fi


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
(python -m girder -p 8999 -d "mongodb://mongo:27017/girder" "$@" > girder_entrypoint.log 2>&1) &

# Wait for it to be done starting
until grep -qi 'engine bus started' girder_entrypoint.log; do sleep 1; done;


# Provision the running instance of girder
pushd /scripts
ansible-playbook -i inventory setup.yml
popd


# Tear down Girder
kill $(pgrep -f girder)

# Start Girder for the container process
python -m girder -p 8989 -d "mongodb://mongo:27017/girder" "$@"
