import sqlite3
from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_curator.codex_runner import runner
from x_curator.executions import execute
from x_curator.worker import process
from x_curator.worker_errors import WorkerFailure


class WorkerFailureTests(PublicationCase):
    def test_provider_failure_preserves_events_and_prevents_duplicate_role(self):
        log = b'{"type":"error","message":"synthetic unavailable"}\n'
        def failed(_):
            raise WorkerFailure("provider unavailable", log)
        with self.assertRaises(WorkerFailure):
            execute(self.db, self.token, "research", "synthetic", failed)
        row = self.db.execute("SELECT log,finished FROM executions").fetchone()
        self.assertEqual((row[0], row[1]), (log, None))
        with self.assertRaises(sqlite3.IntegrityError):
            execute(self.db, self.token, "research", "synthetic", lambda _: self.fail("must not call twice"))

    def test_api_key_login_does_not_start_a_model(self):
        response = type("Status", (), {"stdout": b"Logged in using an API key", "stderr": b""})()
        with patch("x_curator.codex_runner.shutil.which", return_value="synthetic-codex"), patch("x_curator.codex_profile.subprocess.run", return_value=response) as run:
            with self.assertRaisesRegex(WorkerFailure, "subscription login required"):
                runner(self.db, self.token)
        self.assertEqual(run.call_count, 1)

    def test_unexpected_reader_failure_remains_retryable_work(self):
        job = dict(self.db.execute("SELECT * FROM jobs").fetchone())
        with patch("x_curator.worker_process.research", side_effect=RuntimeError("reader needs recovery")):
            result = process(self.db, self.root, None, job)
        self.assertEqual(result["state"], "retry")
        self.assertIn("reader needs recovery", self.db.execute("SELECT action FROM jobs").fetchone()[0])
