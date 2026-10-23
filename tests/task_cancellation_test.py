import unittest

from unittest import mock

from girder_worker.utils import is_revoked


class TestCancellation(unittest.TestCase):

    @mock.patch('girder_worker.utils._worker_inspector')
    def test_is_revoked(self, _worker_inspector):
        task = mock.MagicMock()
        task.request.parent_id = None
        task.request.id = '123'
        task.request.hostname = 'hard@worker'

        worker_inspector = mock.MagicMock()
        _worker_inspector.return_value = worker_inspector
        worker_inspector.revoked.return_value = {
            task.request.hostname: [task.request.id]
        }

        # Revoked
        self.assertTrue(is_revoked(task))

        # Not revoked
        task.request.id = '456'
        self.assertFalse(is_revoked(task))

    @mock.patch('girder_worker.task.is_revoked')
    def test_canceled_is_latched(self, is_revoked):
        from girder_worker.app import app, Task

        @app.task(base=Task, bind=True)
        def task(self):
            pass

        # Once the revoked list reports the cancel, a later fetch that times out
        # to an empty list must not un-cancel the task.
        is_revoked.side_effect = [False, True, False]
        task.push_request()
        try:
            self.assertFalse(task.canceled)
            self.assertTrue(task.canceled)
            self.assertTrue(task.canceled)
        finally:
            task.pop_request()
        self.assertEqual(is_revoked.call_count, 2)
