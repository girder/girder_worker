#!/bin/bash

# Usage: entrypoint.sh <user_id> <group_id> <command to run>

# Add 'worker' user and group matching requested user_id and group_id
group_id=$2
user_id=$1
groupadd -o -g $group_id -r worker
useradd -o -u $user_id --create-home -r -g worker worker

# Requote arguments to account for argument with spaces
quoted_args=''
for i in "${@:3}"; do
    quoted_args="$quoted_args \"${i//\"/\\\"}\""
done

# Execute command as `worker` user
export HOME=/home/worker
exec su -m worker -c "$quoted_args"
