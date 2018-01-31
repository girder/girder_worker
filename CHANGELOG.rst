=============
Release Notes
=============

This is the summary list of changes to Girder Worker between each release. For full
details, see the commit logs at https://github.com/girder/girder_worker

Unreleased
==========

Added Features
--------------

Bug fixes
---------

Changes
-------

Deprecations
------------

DevOps
------

Removals
--------

Security Fixes
--------------

Girder Worker 0.4.1
===================

Bug fixes
---------

* Allow use of default container_args param. (`#268 <https://github.com/girder/girder_worker/pull/268>`_)

Changes
-------

* Remove container by default in docker mode, at end of run. (`#264 <https://github.com/girder/girder_worker/pull/264>`_)
* Refactor JobManager to use Tee objects for stderr/stdout redirection. (`#260 <https://github.com/girder/girder_worker/pull/260>`_)
