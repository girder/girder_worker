#!/bin/bash

# If /girder_worker/setup.py exists then we've
# mounted girder_worker at run time,  make sure it
# is properly installed before continuing
if [ -e /girder_worker/setup.py ]; then
    pip uninstall -y girder-worker
    pip install -e /girder_worker
fi

# If /girder_worker/setup.py exists then we've
# mounted girder_worker at run time,  make sure it
# is properly installed before continuing
if [ -e /girder_worker/tests/integration/common_tasks/setup.py ]; then
    pip uninstall -y common-tasks
    pip install -e /girder_worker/tests/integration/common_tasks/
fi

sudo -u worker python -m girder_worker -l info
