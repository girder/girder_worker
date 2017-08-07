from importlib import import_module

import six
from stevedore import extension
import celery

#: Defines the namespace used for plugin entrypoints
NAMESPACE = 'girder_worker_plugins'


def _import_module(module_name):
    """Try to import a module given as a string."""
    module = None
    try:
        module = import_module(module_name)
    except ImportError:
        import traceback
        traceback.print_exc()
        print('Problem importing %s' % module_name)
    return module


def _handle_entrypoint_errors(mgr, entrypoint, exc):
    print('Problem loading plugin %s, skipping' % entrypoint.name)


def get_extension_manager(app=None):
    """Get an extension manager for the plugin namespace."""
    if app is None:
        app = celery.current_app

    return extension.ExtensionManager(
        namespace=NAMESPACE,
        invoke_on_load=True,
        invoke_args=(app,),
        on_load_failure_callback=_handle_entrypoint_errors
    )


def get_task_imports(ext):
    """Return a list of task modules provided by an extension."""
    try:
        includes = ext.obj.task_imports()
    except Exception:
        import traceback
        traceback.print_exc()
        print('Problem instantiating plugin %s, skipping' % ext.name)
        includes = []
    return includes


def get_core_task_modules(app=None):
    """Return task modules defined by core."""
    return get_task_imports(get_extension_manager(app=app)['core'])


def get_plugin_task_modules(app=None):
    """Return task modules defined by plugins."""
    includes = []
    for ext in get_extension_manager(app=app):
        if ext.name != 'core':
            includes.extend(get_task_imports(ext))
    return includes


def import_all_includes(core=True):
    """Import all task modules for their side-effects."""
    if core:
        for module in get_core_task_modules():
            _import_module(module)

    for module in get_plugin_task_modules():
        _import_module(module)


def get_extensions(app=None):
    """Get a list of install extensions."""
    return [ext.name for ext in get_extension_manager(app)]


def get_module_tasks(module_name, celery_only=False):
    """Get all tasks defined in a python module.

    :param str module_name: The importable module name
    :param bool celery_only: If true, only return celery tasks
    """
    # Import inside the function scope to prevent circular dependencies.
    from . import describe
    from .app import app

    module = _import_module(module_name)
    tasks = {}
    celery_tasks = app.tasks.keys()

    if module is None:
        return tasks

    for name, func in six.iteritems(vars(module)):
        full_name = '%s.%s' % (module_name, name)
        if celery_only and full_name not in celery_tasks:
            # filter out non-celery tasks
            continue

        if not hasattr(func, '__call__'):
            # filter out objects that are not callable
            continue

        try:
            describe.get_description_attribute(func)
            tasks[full_name] = func
        except describe.MissingDescriptionException:
            pass
    return tasks


def get_extension_tasks(extension, app=None, celery_only=False):
    """Get the tasks defined by a girder_worker extension."""

    manager = get_extension_manager(app)
    imports = get_task_imports(manager[extension])
    tasks = {}
    for module_name in imports:
        tasks.update(get_module_tasks(module_name, celery_only))

    return tasks
