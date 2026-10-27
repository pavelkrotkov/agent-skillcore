import sqlite3
from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_curator.publication import publish
from x_curator.verdicts import approved


class PublicationFenceTests(PublicationCase):
    def test_unrelated_commit_during_every_proof_does_not_restart_or_block_writer(self):
        proposal, review = self.approved_executions()
        self.db.execute('CREATE TABLE unrelated_progress (value INTEGER)')
        other = sqlite3.connect(self.root / 'curator.sqlite3', timeout=0.05)
        def verify(*args):
            result = approved(*args)
            with other:
                other.execute('INSERT INTO unrelated_progress VALUES (1)')
            return result
        try:
            with patch('x_curator.publication.approved', side_effect=verify) as verification:
                identity = publish(self.db, self.root, self.token, proposal, review)
            self.assertEqual(verification.call_count, 2)
        finally:
            other.close()
        self.assertEqual(self.db.execute('SELECT count(*) FROM unrelated_progress').fetchone()[0], 2)
        self.assertEqual(self.db.execute('SELECT id,state FROM publications').fetchone()[:], (identity, 'published'))
        self.assertEqual(self.db.execute('SELECT count(*) FROM executions').fetchone()[0], 2)

    def test_changed_review_is_rejected_after_first_full_proof(self):
        proposal, review = self.approved_executions()
        other = sqlite3.connect(self.root / 'curator.sqlite3', timeout=0.05)
        def corrupt(*args):
            result = approved(*args)
            with other:
                other.execute("UPDATE executions SET output='changed' WHERE id=?", (review,))
            return result
        try:
            with patch('x_curator.publication.approved', side_effect=corrupt):
                with self.assertRaises(ValueError):
                    publish(self.db, self.root, self.token, proposal, review)
        finally:
            other.close()
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
        self.assertFalse(self.db.in_transaction)
