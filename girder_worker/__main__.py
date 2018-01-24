from six.moves.configparser import NoSectionError, NoOptionError

from . import config
from .app import app
from .entrypoint import get_core_task_modules, get_plugin_task_modules


def main():
    try:
        include_core_tasks = config.getboolean(
            'girder_worker', 'core_tasks')
    except (NoSectionError, NoOptionError):
        include_core_tasks = True

    if include_core_tasks:
        app.conf.update({
            'CELERY_IMPORTS': get_core_task_modules()
        })

    app.conf.update({
        'CELERY_INCLUDE': get_plugin_task_modules()
    })
    app.worker_main()


if __name__ == '__main__':
    main()
