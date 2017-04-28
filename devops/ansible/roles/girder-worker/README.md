girder.worker
====================
An Ansible role to install [Girder Worker](https://github.com/girder/girder_worker).

Further documentation on Girder Worker can be found [here](https://girder-worker.readthedocs.io).

Requirements
------------

Ubuntu 14.04/16.04.

Role Variables
--------------

| parameter                    | required | default             | comments                                                                                                                    |
| --------------------------   | -------- | --------------------| ----------------------------------------------------------------------------------------------------------------------------|
| girder_worker_install_source | no       | pypi                | Must be "pypi" or "git" to determine where to fetch the source code from. If git, the pip install will be editable.         |
| girder_worker_pypi_version   | no       | none                | The version to be passed to pip install, only applicable if `girder_worker_install_source` is "pypi".                       |
| girder_worker_git_version    | no       | master              | Git commit-ish for fetching Girder Worker.                                                                                  |
| girder_worker_virtualenv     | no       | none                | Path to a Python virtual environment to install Girder Worker in (doesn't have to exist yet).                               |
| girder_worker_path           | no       | $HOME/girder_worker | Path to install Girder Worker in. Only applicable if `girder_worker_install_source` is "git".                               |
| girder_worker_update         | no       | no                  | Whether provisioning should fetch new versions. (`pip --upgrade` or `git pull` depending on `girder_worker_install_source`) |
| girder_worker_plugins        | no       | none                | List of Girder Worker plugins to install.                                                                                   |
| girder_worker_daemonize      | no       | yes                 | Whether to install the relevant service files (systemd or upstart).                                                         |
| girder_worker_start          | no       | yes                 | Whether to start the installed service (requires `girder_worker_daemonize`).                                                |
| girder_worker_enabled        | no       | yes                 | Whether to enable the installed service (requires `girder_worker_daemonize`).                                               |
| girder_worker_user           | no       | `ansible_user_id`   | The user to run Girder Worker as, this is only used if `girder_worker_daemonize` is true.                                   |


Examples
--------

Examples can be found [here](https://github.com/girder/girder_worker/tree/master/devops/ansible/examples).
