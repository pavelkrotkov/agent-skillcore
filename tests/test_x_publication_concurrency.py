import sqlite3
from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_curator.publication import publish
from x_curator.verdicts import approved
from x_curator.read_set import ChangedDependencies


class PublicationConcurrencyTests(PublicationCase):
    def conflicted(self, phase):
        proposal, review = self.approved_executions()
        other = sqlite3.connect(self.root / 'curator.sqlite3', timeout=0.05)
        seen = self.approval_reads = []
        def verify(*args):
            packet = approved(*args)
            seen.append(other.execute('SELECT state FROM publications').fetchone())
            if phase is None or len(seen) == phase:
                with other:
                    other.execute("UPDATE jobs SET action=action||' concurrent progress'")
            return packet
        try:
            with patch('x_curator.publication.approved', side_effect=verify):
                result = publish(self.db, self.root, self.token, proposal, review)
        finally:
            other.close()
        self.assertEqual(self.db.execute('SELECT attempts,max_attempts FROM jobs').fetchone()[:], (1, 3))
        self.assertEqual(self.db.execute('SELECT count(*) FROM executions').fetchone()[0], 2)
        self.assertFalse(self.db.in_transaction)
        return result, seen

    def test_first_phase_conflict_retries_same_lease_and_review_without_new_model_calls(self):
        identity, seen = self.conflicted(1)
        self.assertEqual(len(seen), 3)
        self.assertEqual(self.db.execute('SELECT id,state FROM publications').fetchone()[:], (identity, 'published'))

    def test_final_phase_conflict_retains_and_reuses_prepared_publication(self):
        identity, seen = self.conflicted(2)
        self.assertEqual(seen, [None, ('prepared',), ('prepared',), ('prepared',)])
        row = self.db.execute('SELECT * FROM publications').fetchone()
        self.assertEqual((row['id'], row['state']), (identity, 'published'))
        self.assertEqual((self.root / row['path']).read_bytes(), row['body'])

    def test_persistent_snapshot_conflicts_are_bounded_and_leave_source_unpublished(self):
        with self.assertRaises(ChangedDependencies):
            self.conflicted(None)
        self.assertEqual(len(self.approval_reads), 3)
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT state,attempts FROM jobs').fetchone()[:], ('leased', 1))
        self.assertFalse(self.db.in_transaction)
