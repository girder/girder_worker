from importlib import import_module
import pkg_resources as pr

from .app import app


def get_plugin_tasks(ep):
    """Return a list of modules containing plugin tasks.

    :param ep: An entrypoint object defined by a plugin
    :returns: A list of importable modules
    """
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


def _import_module(module):
    """Try to import a module given as a string."""
    try:
        import_module(module)
    except ImportError:
        import traceback
        traceback.print_exc()
        print('Problem importing %s' % module)


def _get_entrypoints():
    """Get a list of entrypoints from package resources.

    :returns:
        A tuple whose first element is the core entrypoint
        and whose second element is a list of entrypoints
        provided by plugins.
    """
    entrypoints = []
    core = None
    for ep in pr.iter_entry_points(group='girder_worker_plugins'):
        # If this is the girder_worker EntryPoint
        if ep.module_name == __package__:
            core = ep
        else:
            entrypoints.append(ep)
    return core, entrypoints


def get_core_task_modules():
    """Return task modules defined by core."""
    core = _get_entrypoints()[0]
    return get_plugin_tasks(core)


def get_plugin_task_modules():
    """Return task modules defined by plugins."""
    includes = []
    for entrypoint in _get_entrypoints()[1]:
        includes.extend(get_plugin_tasks(entrypoint))
    return includes


def import_all_includes(core=True):
    """Import all task modules for their side-effects."""
    if core:
        for module in get_core_task_modules():
            _import_module(module)

    for module in get_plugin_task_modules():
        _import_module(module)
