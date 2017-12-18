#!/bin/bash

set -e

source_dir="${1}"
binary_dir="${2}"
rm -rf ve/
virtualenv ve
. ve/bin/activate
cd ${source_dir}
python2 setup.py sdist --dist-dir ${binary_dir}
cd ${binary_dir}
pip2 install ./girder-worker-*.tar.gz
which girder-worker
girder-worker-config list
