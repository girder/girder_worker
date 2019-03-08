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

Girder Worker 0.6.0
==========

Added Features
--------------

Bug fixes
---------

Changes
-------

* Remove legacy girder_worker code (`#332 <https://github.com/girder/girder_worker/pull/332>`_)

Deprecations
------------

DevOps
------

Removals
--------

Security Fixes
--------------


Girder Worker 0.5.1
===================

Added Features
--------------
* Move the remote worker plugin from Girder to Girder Worker (`#311 <https://github.com/girder/girder_worker/pull/311>`_)
* Support nvidia-docker version 2.0 (`#303 <https://github.com/girder/girder_worker/pull/303>`_)
* Add ability to upload job artifacts from docker (`#300 <https://github.com/girder/girder_worker/pull/300>`_)

Bug fixes
---------

* Explicitly load configuration after app instantiation(`#284 <https://github.com/girder/girder_worker/pull/284>`_)
* Resolve issues with integration tests from upstream change  (`#335 <https://github.com/girder/girder_worker/pull/335>`_)

Changes
-------
* Various updates to transforms (`#289 <https://github.com/girder/girder_worker/pull/289>`_, `#292 <https://github.com/girder/girder_worker/pull/292>`_, `#305 <https://github.com/girder/girder_worker/pull/305>`_, `#323 <https://github.com/girder/girder_worker/pull/323>`_)
* Documentation improvements (`#288 <https://github.com/girder/girder_worker/pull/288>`_, `#308 <https://github.com/girder/girder_worker/pull/308>`_, `#309 <https://github.com/girder/girder_worker/pull/309>`_)

Deprecations
------------

DevOps
------

Removals
--------

Security Fixes
--------------


Girder Worker 0.5.0
===================



Bug fixes
---------

* Resolve multiple issues related to broken chord functionality
  (`#280 <https://github.com/girder/girder_worker/pull/280>`_, `#282 <https://github.com/girder/girder_worker/pull/282>`_)
* Use cherrypy.request.app instead of ImportException to determine signal context (`#275 <https://github.com/girder/girder_worker/pull/275>`_)

Changes
-------

* Volume transforms renamed to BindMountVolume (`#273 <https://github.com/girder/girder_worker/pull/273>`_)
* Refactor signals to introduce 'context' in which code is being executed (`#271 <https://github.com/girder/girder_worker/pull/271>`_)
* Move entrypoint based task descovery earlier in application initialization (`#278 <https://github.com/girder/girder_worker/pull/278?>`_)


Girder Worker 0.4.1
===================

Bug fixes
---------

* Allow use of default container_args param. (`#268 <https://github.com/girder/girder_worker/pull/268>`_)

Changes
-------

* Remove container by default in docker mode, at end of run. (`#264 <https://github.com/girder/girder_worker/pull/264>`_)
* More robust standard pipe handling in tasks that communicate with Girder jobs. (`#260 <https://github.com/girder/girder_worker/pull/260>`_)
