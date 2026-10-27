import sqlite3
from unittest.mock import patch

from x_prepared_fixtures import PreparedCase
from x_curator.publication_recovery import complete
from x_curator.prepared_proof import verify_publication
from x_curator.read_set import ChangedDependencies


class PreparedConflictTests(PreparedCase):
    def test_worker_claim_during_verification_prevents_recovery(self):
        other = sqlite3.connect(self.root / 'curator.sqlite3', timeout=0.05)
        def claimed(*args):
            result = verify_publication(*args)
            with other:
                other.execute("UPDATE jobs SET state='leased',token='synthetic-owner',lease_until=1")
            return result
        try:
            with patch('x_curator.prepared_proof.verify_publication', side_effect=claimed):
                with self.assertRaises(ChangedDependencies):
                    complete(self.db, self.root, self.identity, 'Concurrent owner must win')
        finally:
            other.close()
        self.assertEqual(self.db.execute('SELECT state FROM publications').fetchone()[0], 'prepared')
        with self.assertRaisesRegex(ValueError, 'still owned'):
            complete(self.db, self.root, self.identity, 'Expired ownership also rejects')

    def test_foreign_approval_cannot_complete_another_source(self):
        with self.db:
            self.db.execute("INSERT INTO jobs(account,id,created) VALUES ('foreign','1',0)")
            self.db.execute("UPDATE attempts SET account='foreign'")
        with self.assertRaisesRegex(ValueError, 'different source'):
            complete(self.db, self.root, self.identity, 'Foreign approval must reject')
        self.assertEqual(self.db.execute('SELECT state FROM publications').fetchone()[0], 'prepared')

    def test_changed_evidence_fails_closed(self):
        with self.db:
            self.db.execute("UPDATE captures SET sha='changed'")
        with self.assertRaisesRegex(ValueError, 'tampered capture'):
            complete(self.db, self.root, self.identity, 'Changed evidence must reject')
        self.assertEqual(self.ledger(), self.before)

    def test_interruption_before_commit_preserves_prepared_work(self):
        with patch('x_curator.publication_recovery.private_target', side_effect=OSError('synthetic disk failure')):
            with self.assertRaises(OSError):
                complete(self.db, self.root, self.identity, 'Interrupted completion')
        self.assertEqual(self.db.execute('SELECT state FROM publications').fetchone()[0], 'prepared')
        self.assertEqual(self.db.execute('SELECT count(*) FROM publication_recoveries').fetchone()[0], 0)
        self.assertEqual(self.ledger(), self.before)
