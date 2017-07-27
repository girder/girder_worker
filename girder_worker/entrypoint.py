from importlib import import_module

from stevedore import extension
import celery

#: Defines the namespace used for plugin entrypoints
NAMESPACE = 'girder_worker_plugins'


def _import_module(module):
    """Try to import a module given as a string."""
    try:
        import_module(module)
    except ImportError:
        import traceback
        traceback.print_exc()
        print('Problem importing %s' % module)


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
