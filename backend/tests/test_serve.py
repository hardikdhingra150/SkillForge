import unittest
from unittest import mock

from app import serve


class StartWithoutTheDatabaseTests(unittest.TestCase):
    def test_a_failed_migration_does_not_stop_the_api(self):
        with mock.patch.object(serve.command, "upgrade", side_effect=RuntimeError("tenant/user not found")), \
                mock.patch.object(serve.threading, "Thread") as thread, \
                mock.patch("uvicorn.run") as run:
            serve.main()
        run.assert_called_once()
        thread.return_value.start.assert_called_once()

    def test_the_migration_is_retried_until_it_works(self):
        attempts = iter([RuntimeError("down"), RuntimeError("down"), None])

        def upgrade(*_args):
            error = next(attempts)
            if error:
                raise error

        waits = []
        with mock.patch.object(serve.command, "upgrade", side_effect=upgrade):
            serve.keep_migrating(sleep=waits.append)
        self.assertEqual(waits, [serve.RETRY_SECONDS, serve.RETRY_SECONDS])

    def test_a_working_database_needs_no_retry(self):
        with mock.patch.object(serve.command, "upgrade"), mock.patch.object(serve.threading, "Thread") as thread, \
                mock.patch("uvicorn.run"):
            serve.main()
        thread.assert_not_called()
