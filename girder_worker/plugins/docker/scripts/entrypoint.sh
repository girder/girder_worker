#!/bin/bash

# Usage: entrypoint.sh <user_id> <group_id> <command to run>
sudo groupadd -o -g $2 -r worker
sudo useradd -o -u $1 --create-home -r -g worker worker
exec ${@:3}
