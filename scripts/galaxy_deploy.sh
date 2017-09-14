#!/bin/bash
set -e

# Ansible role repo to deploy to
readonly ANSIBLE_ROLE_GITHUB_ORG="girder"
readonly ANSIBLE_ROLE_GITHUB_REPO="ansible-role-girder-worker"

readonly SUBTREE_PREFIX="devops/ansible/roles/girder-worker"
readonly SUBTREE_DEST_REPO="git@github.com:$ANSIBLE_ROLE_GITHUB_ORG/$ANSIBLE_ROLE_GITHUB_REPO.git"
readonly SUBTREE_DEST_BRANCH="master"

# Push any changes that have occurred
git reset --hard
git branch ansible-role-subtree
git filter-branch --subdirectory-filter "$SUBTREE_PREFIX" ansible-role-subtree
git push "$SUBTREE_DEST_REPO" ansible-role-subtree:"$SUBTREE_DEST_BRANCH"

# Install ansible for ansible-galaxy
pip install ansible

# Import the changes into Ansible Galaxy
ansible-galaxy login --github-token="$ANSIBLE_GALAXY_GITHUB_TOKEN"
ansible-galaxy import "$ANSIBLE_ROLE_GITHUB_ORG" "$ANSIBLE_ROLE_GITHUB_REPO"
