import functools
import mock
from StringIO import StringIO
import unittest

from girder_worker import entrypoint
from girder_worker.__main__ import main


class set_namespace(object):
    def __init__(self, namespace):
        self.namespace = namespace

    def __call__(self, func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            original = entrypoint.NAMESPACE
            entrypoint.NAMESPACE = self.namespace
            try:
                result = func(*args, **kwargs)
            finally:
                entrypoint.NAMESPACE = original
            return result
        return wrapped


class TestTaskPlugin(unittest.TestCase):
    @set_namespace('girder_worker.test.valid_plugins')
    def test_get_extension_manager(self):
        mgr = entrypoint.get_extension_manager()
        names = sorted(mgr.names())
        self.assertEqual(names, ['core', 'plugin1', 'plugin2'])

    @set_namespace('girder_worker.test.valid_plugins')
    def test_get_core_task_modules(self):
        modules = entrypoint.get_core_task_modules()
        self.assertEqual(modules, ['os.path'])

    @set_namespace('girder_worker.test.valid_plugins')
    @mock.patch('girder_worker.entrypoint.import_module')
    def test_import_all_includes(self, imp):
        entrypoint.import_all_includes()
        imp.assert_has_calls(
            (mock.call('os.path'), mock.call('girder_worker.tests.tasks')),
            any_order=True
        )

    @set_namespace('girder_worker.test.invalid_plugins')
    @mock.patch('sys.stderr', new_callable=StringIO)
    @mock.patch('sys.stdout', new_callable=StringIO)
    def test_invalid_plugins(self, stdout, stderr):
        entrypoint.get_plugin_task_modules()
        lines = stdout.getvalue().splitlines()
        self.assertEqual(len(lines), 4)
        for line in lines:
            self.assertRegexpMatches(
                line, '^Problem.*(exception[12]|invalid|import), skipping$'
            )

        self.assertEqual(entrypoint.get_core_task_modules(), ['os.path'])

    @mock.patch('girder_worker.__main__.app')
    def test_core_plugin(self, app):
        main()
        app.conf.update.assert_any_call({'CELERY_IMPORTS':
                                         ['girder_worker.tasks']})

    @set_namespace('girder_worker.test.valid_plugins')
    @mock.patch('girder_worker.__main__.app')
    def test_external_plugins(self, app):
        main()
        app.conf.update.assert_any_call({'CELERY_IMPORTS':
                                         ['os.path']})
        app.conf.update.assert_any_call({'CELERY_INCLUDE':
                                         ['girder_worker.tests.tasks']})

    @set_namespace('girder_worker.test.valid_plugins')
    @mock.patch('girder_worker.__main__.app')
    def test_get_extensions(self, app):
        main()
        extensions = sorted(entrypoint.get_extensions())
        self.assertEqual(extensions, ['core', 'plugin1', 'plugin2'])

    @set_namespace('girder_worker.test.valid_plugins')
    @mock.patch('girder_worker.__main__.app')
    def test_get_module_tasks(self, app):
        main()
        extensions = sorted(entrypoint.get_module_tasks('girder_worker.tests.tasks'))
        self.assertEqual(extensions, [
            'girder_worker.tests.tasks.celery_task',
            'girder_worker.tests.tasks.function_task'
        ])

    @set_namespace('girder_worker.test.valid_plugins')
    @mock.patch('girder_worker.__main__.app')
    def test_get_extension_tasks(self, app):
        main()
        extensions = sorted(entrypoint.get_extension_tasks('plugin2'))
        self.assertEqual(extensions, [
            'girder_worker.tests.tasks.celery_task',
            'girder_worker.tests.tasks.function_task'
        ])

    @set_namespace('girder_worker.test.valid_plugins')
    @mock.patch('girder_worker.__main__.app')
    def test_get_extension_tasks_celery(self, app):
        main()
        extensions = sorted(entrypoint.get_extension_tasks('plugin2', celery_only=True))
        self.assertEqual(extensions, [
            'girder_worker.tests.tasks.celery_task'
        ])
