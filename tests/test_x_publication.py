from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_curator.publication import publish
from x_curator.publication_audit import audit, replay_file
from x_curator.verdicts import approved


class PublicationTests(PublicationCase):
    def test_nested_git_checkout_rejects_private_publication(self):
        proposal, review = self.approved_executions()
        (self.root / "wiki/.git").mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "outside Git"):
            publish(self.db, self.root, self.token, proposal, review)
        self.assertEqual(self.db.execute("SELECT state FROM jobs").fetchone()[0], "leased")

    def test_interruption_after_file_write_replays_before_marking_complete(self):
        proposal, review = self.approved_executions()
        with patch("x_curator.publication.approved", side_effect=[approved(self.db, self.token, proposal, review), RuntimeError("interrupted")]):
            with self.assertRaisesRegex(RuntimeError, "interrupted"):
                publish(self.db, self.root, self.token, proposal, review)
        row = self.db.execute("SELECT * FROM publications").fetchone()
        self.assertEqual(row["state"], "prepared")
        self.assertEqual((self.root / row["path"]).read_bytes(), row["body"])
        self.assertEqual(self.db.execute("SELECT state FROM jobs").fetchone()[0], "leased")
        identity = publish(self.db, self.root, self.token, proposal, review)
        self.assertEqual(identity, row["id"])
        self.assertEqual(self.db.execute("SELECT state FROM jobs").fetchone()[0], "published")

    def test_catalog_invalidation_and_replay_keep_job_unresolved(self):
        proposal, review = self.approved_executions()
        identity = publish(self.db, self.root, self.token, proposal, review)
        row = self.db.execute("SELECT * FROM publications").fetchone()
        (self.root / row["path"]).unlink()
        self.assertEqual(audit(self.db, self.root), [identity])
        self.assertEqual(self.db.execute("SELECT state FROM jobs").fetchone()[0], "retry")
        replay_file(self.db, self.root, identity)
        self.assertEqual((self.root / row["path"]).read_bytes(), row["body"])
        self.assertEqual(self.db.execute("SELECT state FROM publications").fetchone()[0], "invalid")

    def test_conflicting_file_prevents_completion_without_overwriting(self):
        proposal, review = self.approved_executions()
        with patch("x_curator.publication.write_verified", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                publish(self.db, self.root, self.token, proposal, review)
        row = self.db.execute("SELECT * FROM publications").fetchone()
        target = self.root / row["path"]
        target.parent.mkdir(parents=True)
        target.write_text("unrelated concurrent edit")
        with self.assertRaisesRegex(ValueError, "conflict"):
            publish(self.db, self.root, self.token, proposal, review)
        self.assertEqual(target.read_text(), "unrelated concurrent edit")
        self.assertEqual(self.db.execute("SELECT state FROM jobs").fetchone()[0], "leased")
