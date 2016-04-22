#!/bin/bash

# Usage: entrypoint.sh <user_id> <group_id> <command to run>
groupadd -o -g $2 -r worker
useradd -o -u $1 --create-home -r -g worker worker
exec sudo -u worker ${@:3}
