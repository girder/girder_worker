import re

from girder_worker import entrypoint
from girder_worker.__main__ import main
from girder_worker.app import app

from girder_worker_utils import decorators
from girder_worker_utils import types

import mock
import pytest
import six


def setup_function(func):
    if hasattr(func, 'namespace'):
        namespace = func.namespace.args[0]
        func.original = entrypoint.NAMESPACE
        entrypoint.NAMESPACE = namespace


def teardown_function(func):
    if hasattr(func, 'original'):
        entrypoint.NAMESPACE = func.original


@pytest.mark.namespace('girder_worker._test_plugins.valid_plugins')
def test_get_extension_manager():
    mgr = entrypoint.get_extension_manager()
    names = sorted(mgr.names())
    assert names == ['core', 'plugin1', 'plugin2']


@pytest.mark.skipif(six.PY3, reason='Python 2 only')
@pytest.mark.namespace('girder_worker._test_plugins.valid_plugins')
def test_get_core_task_modules():
    modules = entrypoint.get_core_task_modules()
    assert modules == ['os.path']


@pytest.mark.namespace('girder_worker._test_plugins.valid_plugins')
def test_import_all_includes():
    with mock.patch('girder_worker.entrypoint.import_module') as imp:
        entrypoint.import_all_includes()
        imp.assert_has_calls(
            (mock.call('os.path'), mock.call('girder_worker._test_plugins.tasks')),
            any_order=True)


@pytest.mark.namespace('girder_worker._test_plugins.invalid_plugins')
def test_invalid_plugins(capsys):
    entrypoint.get_plugin_task_modules()
    out, err = capsys.readouterr()
    # Note:  last element of split('\n') will be an empty line
    out = out.split('\n')[:-1]

    assert len(out) == 4
    for line in out:
        assert re.search('^Problem.*(exception[12]|invalid|import), skipping$', line)

    assert entrypoint.get_core_task_modules() == ['os.path']


@pytest.mark.skipif(six.PY3, reason='Python 2 only')
def test_core_plugin():
    with mock.patch('girder_worker.__main__.app') as app:
        main()
        app.conf.update.assert_any_call({'CELERY_IMPORTS':
                                         ['girder_worker.tasks']})


@pytest.mark.namespace('girder_worker._test_plugins.valid_plugins')
def test_external_plugins():
    with mock.patch('girder_worker.__main__.app') as app:
        main()
        if six.PY2:
            app.conf.update.assert_any_call({'CELERY_IMPORTS':
                                             ['os.path']})
        app.conf.update.assert_any_call({'CELERY_INCLUDE':
                                         ['girder_worker._test_plugins.tasks']})


@pytest.mark.namespace('girder_worker._test_plugins.valid_plugins')
def test_get_extensions():
    with mock.patch('girder_worker.__main__.app'):
        main()
        extensions = sorted(entrypoint.get_extensions())
        assert extensions == ['core', 'plugin1', 'plugin2']


@pytest.mark.namespace('girder_worker._test_plugins.valid_plugins')
def test_get_module_tasks():
    with mock.patch('girder_worker.__main__.app'):
        main()
        extensions = sorted(entrypoint.get_module_tasks('girder_worker._test_plugins.tasks'))
        assert extensions == [
            'girder_worker._test_plugins.tasks.celery_task',
            'girder_worker._test_plugins.tasks.function_task'
        ]


@pytest.mark.namespace('girder_worker._test_plugins.valid_plugins')
def test_get_extension_tasks():
    with mock.patch('girder_worker.__main__.app'):
        main()
        extensions = sorted(entrypoint.get_extension_tasks('plugin2'))
        assert extensions == [
            'girder_worker._test_plugins.tasks.celery_task',
            'girder_worker._test_plugins.tasks.function_task'
        ]


@pytest.mark.namespace('girder_worker._test_plugins.valid_plugins')
def test_get_extension_tasks_celery():
    with mock.patch('girder_worker.__main__.app'):
        main()
        extensions = sorted(entrypoint.get_extension_tasks('plugin2', celery_only=True))
        assert extensions == [
            'girder_worker._test_plugins.tasks.celery_task'
        ]


def test_register_extension():

    @decorators.argument('n', types.Integer)
    def echo(n):
        return n

    @app.task
    @decorators.argument('n', types.Integer)
    def echo_celery(n):
        return n

    tasks = {
        '%s.echo' % __name__: echo,
        '%s.echo_celery' % __name__: echo_celery
    }
    entrypoint.register_extension('echo_tasks', tasks)

    exts = entrypoint.get_extensions()
    assert 'echo_tasks' in exts
    assert entrypoint.get_extension_tasks('echo_tasks') == tasks

    celery_tasks = entrypoint.get_extension_tasks('echo_tasks', celery_only=True)
    assert list(celery_tasks.keys()) == ['%s.echo_celery' % __name__]
