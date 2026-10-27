import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from x_fixtures import open_store
from x_curator.__main__ import main


class ProcessBoundaryTests(unittest.TestCase):
    def test_database_and_sidecar_symlinks_cannot_escape_private_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkout = root / "repo"
            (checkout / ".git").mkdir(parents=True)
            for name in ("curator.sqlite3", "curator.sqlite3-wal", "curator.sqlite3-shm", "curator.sqlite3-journal"):
                private = root / name
                private.mkdir()
                (private / name).symlink_to(checkout / "leak")
                with self.assertRaisesRegex(ValueError, "symlink"):
                    open_store(private)
                self.assertFalse((checkout / "leak").exists())

    def test_blocked_collection_returns_nonzero_with_machine_readable_status(self):
        with tempfile.TemporaryDirectory() as directory:
            client = Mock(account="synthetic-account")
            client.fetch.return_value = (429, b"limited")
            output = io.StringIO()
            args = ["curator", "--state", directory, "collect", "likes"]
            with patch("sys.argv", args), patch("x_curator.live_dispatch.XClient", return_value=client):
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(), 2)
            self.assertIn('"reason": "http_429"', output.getvalue())


if __name__ == "__main__":
    unittest.main()
