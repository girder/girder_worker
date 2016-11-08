import unittest
import mock
import girder_worker
from girder_worker.__main__ import main
from pkg_resources import EntryPoint


def mock_plugin(task_list):
    class _MockPlugin(girder_worker.GirderWorkerPluginABC):
        def __init__(self, app, *args, **kwargs):
            pass

        def task_imports(self):
            return task_list

    return _MockPlugin


class TestTaskPlugin(unittest.TestCase):
    @mock.patch('girder_worker.__main__.pr')
    @mock.patch('girder_worker.__main__.app')
    def test_core_plugin(self, app, pr):
        ep = EntryPoint.parse('core = girder_worker:GirderWorkerPlugin')
        ep.load = mock.Mock(return_value=girder_worker.GirderWorkerPlugin)
        pr.iter_entry_points.return_value = [ep]

        main()

        app.conf.update.assert_any_call({'CELERY_IMPORTS': ['girder_worker.tasks']})
        app.conf.update.assert_any_call({'CELERY_INCLUDE': []})


    @mock.patch('girder_worker.__main__.pr')
    @mock.patch('girder_worker.__main__.app')
    def test_core_and_other_plugin(self, app, pr):

        core = EntryPoint.parse('core = girder_worker:GirderWorkerPlugin')
        core.load = mock.Mock(return_value=girder_worker.GirderWorkerPlugin)

        plugin = EntryPoint.parse('mock = mockplugin:MockPlugin')
        plugin.load = mock.Mock(return_value=mock_plugin(['mock.plugin.tasks']))

        pr.iter_entry_points.return_value = [core, plugin]

        main()

        app.conf.update.assert_any_call({'CELERY_IMPORTS': ['girder_worker.tasks']})
        app.conf.update.assert_any_call({'CELERY_INCLUDE': ['mock.plugin.tasks']})

    @mock.patch('girder_worker.__main__.pr')
    @mock.patch('girder_worker.__main__.app')
    def test_multiple_plugins(self, app, pr):

        core = EntryPoint.parse('core = girder_worker:GirderWorkerPlugin')
        core.load = mock.Mock(return_value=girder_worker.GirderWorkerPlugin)

        plugin = EntryPoint.parse('mock = mockplugin:MockPlugin')
        plugin.load = mock.Mock(return_value=mock_plugin(['mock.plugin.tasks']))

        plugin2 = EntryPoint.parse('mock = mockplugin:MockPlugin')
        plugin2.load = mock.Mock(return_value=mock_plugin(['mock.plugin2.tasks']))

        pr.iter_entry_points.return_value = [core, plugin, plugin2]

        main()

        app.conf.update.assert_any_call({'CELERY_IMPORTS': ['girder_worker.tasks']})
        app.conf.update.assert_any_call({'CELERY_INCLUDE': ['mock.plugin.tasks',
                                                            'mock.plugin2.tasks']})


    @mock.patch('girder_worker.__main__.pr')
    @mock.patch('girder_worker.__main__.app')
    @mock.patch('girder_worker.__main__.config')
    def test_exclude_core_tasks(self, config, app, pr):

        core = EntryPoint.parse('core = girder_worker:GirderWorkerPlugin')
        core.load = mock.Mock(return_value=girder_worker.GirderWorkerPlugin)
        pr.iter_entry_points.return_value = [core]
        config.getboolean.return_value = False

        main()

        # Called once with no plugins,  ie.  core_tasks were not added
        app.conf.update.assert_called_once_with({'CELERY_INCLUDE': []})

    @mock.patch('girder_worker.__main__.pr')
    @mock.patch('girder_worker.__main__.app')
    def test_plugin_throws_import_error(self, app, pr):
        core = EntryPoint.parse('core = girder_worker:GirderWorkerPlugin')
        core.load = mock.Mock(side_effect=ImportError("Intentionally throw import error"))
        pr.iter_entry_points.return_value = [core]

        main()

        app.conf.update.assert_any_call({'CELERY_IMPORTS': []})


    @mock.patch('girder_worker.__main__.pr')
    @mock.patch('girder_worker.__main__.app')
    def test_plugin_task_imports_throws_exception(self, app, pr):
        core = EntryPoint.parse('core = girder_worker:GirderWorkerPlugin')
        MockPlugin = mock_plugin([])
        MockPlugin.task_imports = mock.Mock(side_effect=Exception("Intentionally throw exception"))

        core.load = mock.Mock(return_value=MockPlugin)
        pr.iter_entry_points.return_value = [core]

        main()

        app.conf.update.assert_any_call({'CELERY_IMPORTS': []})
