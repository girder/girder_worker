from importlib import import_module

from girder_worker_utils import decorators
import six
from stevedore import extension

try:
    from celery import current_app
except ImportError:
    current_app = None

#: Defines the namespace used for plugin entrypoints
NAMESPACE = 'girder_worker_plugins'

# Define an internal registry for extensions that aren't associated
# with an entrypoint.  This registry is primarily useful for testing
# where one doesn't necessarily want to install a package into the
# environment for a one off test task.
_extensions = {}


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
        app = current_app

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
    return [ext.name for ext in get_extension_manager(app)] + \
        _extensions.keys()


def get_module_tasks(module_name):
    """Get all tasks defined in a python module.

    :param str module_name: The importable module name
    """
    module = _import_module(module_name)
    tasks = {}

    if module is None:
        return tasks

    for name, func in six.iteritems(vars(module)):
        full_name = '%s.%s' % (module_name, name)
        if not hasattr(func, '__call__'):
            # filter out objects that are not callable
            continue

        try:
            decorators.get_description_attribute(func)
            tasks[full_name] = func
        except decorators.MissingDescriptionException:
            pass
    return tasks


def get_extension_tasks(extension, app=None, celery_only=False):
    """Get the tasks defined by a girder_worker extension.

    :param str extension: The extension name
    :param app: The celery app instance
    :param bool celery_only: If true, only return celery tasks
    """

    tasks = {}
    if extension in _extensions:
        tasks = _extensions[extension]
    else:
        manager = get_extension_manager(app)
        imports = get_task_imports(manager[extension])
        tasks = {}
        for module_name in imports:
            tasks.update(get_module_tasks(module_name))

    if celery_only:  # filter celery tasks
        if app is None:
            from .app import app
        tasks = {
            key: tasks[key] for key in tasks if key in app.tasks
        }

    return tasks


def register_extension(name, tasks):
    """Register an extension by name.

    This is an alternative to registering extensions via
    entrypoints.  Its primary use case is for one off tasks
    used in testing.  Using entrypoint extensions is preferred
    because they will be automatically registered, and the
    tasks will have fully resolved python modules that can
    be reused by other tasks and extensions.

    :param str name: The extension name
    :param dict tasks: A mapping from task name to the task function
    """
    global _extensions
    _extensions[name] = tasks
