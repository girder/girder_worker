import pkg_resources as pr
from . import config
from ConfigParser import NoSectionError, NoOptionError
from .app import app


def get_plugin_tasks(ep):
    try:
        plugin_class = ep.load()

    except Exception:
        import traceback
        traceback.print_exc()
        print('Could not load \'%s\', skipping.' % str(ep))
        return []

    try:
        plugin = plugin_class(app)
        return plugin.task_imports()

    except Exception:
        import traceback
        traceback.print_exc()
        print(
            'Problem instantiating plugin %s, skipping.'
            % plugin_class.__name__)
        return []


def main():
    includes = []
    for ep in pr.iter_entry_points(group='girder_worker_plugins'):
        # If this is the girder_worker EntryPoint
        if ep.module_name == __package__:
            # And core_tasks config is True
            include_core_tasks = True
            try:
                include_core_tasks = config.getboolean(
                    'girder_worker', 'core_tasks')
            except (NoSectionError, NoOptionError):
                pass

            if include_core_tasks:
                # Load core tasks in CELERY_IMPORTS
                # Note: CELERY_IMPORTS  guarantees that core tasks
                #       will be loaded before all plugin tasks.
                app.conf.update({
                    'CELERY_IMPORTS': get_plugin_tasks(ep)})
        else:
            includes.extend(get_plugin_tasks(ep))

    app.conf.update({
        'CELERY_INCLUDE': includes
    })

    app.worker_main()

if __name__ == '__main__':
    main()
