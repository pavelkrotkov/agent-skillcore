import sqlite3
from unittest.mock import patch

from x_prepared_fixtures import PreparedCase
from x_curator.publication_recovery import complete
from x_curator.prepared_proof import verify_publication
from x_curator.read_set import ChangedDependencies


class PreparedConcurrentTests(PreparedCase):
    def test_two_completers_cannot_append_duplicate_recovery_receipts(self):
        other = sqlite3.connect(self.root / 'curator.sqlite3', timeout=0.05)
        other.row_factory = sqlite3.Row
        def competing(*args):
            result = verify_publication(*args)
            with patch('x_curator.prepared_proof.verify_publication', side_effect=verify_publication):
                complete(other, self.root, self.identity, 'First concurrent completion')
            return result
        try:
            with patch('x_curator.prepared_proof.verify_publication', side_effect=competing):
                with self.assertRaises(ChangedDependencies):
                    complete(self.db, self.root, self.identity, 'Stale concurrent completion')
        finally:
            other.close()
        repeated = complete(self.db, self.root, self.identity, 'Safe subsequent invocation')
        self.assertTrue(repeated['already_completed'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM publication_recoveries').fetchone()[0], 1)
        self.assertEqual(self.ledger(), self.before)
