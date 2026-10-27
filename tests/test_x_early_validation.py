import time
from unittest.mock import patch
from x_early_validation_fixtures import EarlyCase
from x_curator.publication_audit import audit


class EarlyValidationTests(EarlyCase):
    def test_early_invalid_draft_corrects_after_read_cutoff_and_finishes_once(self):
        self.start = self.at = time.time()
        with patch('time.time', side_effect=lambda: self.at):
            self.assertIsNotNone(self.run_final())
            self.assertEqual(audit(self.db, self.root), [])
        check = self.db.execute('SELECT * FROM quick_checks').fetchone()
        self.assertEqual(check['deadline'] - check['started'], 120)
        self.assertEqual(self.db.execute('SELECT count(*) FROM attempts').fetchone()[0], 1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM sqlite_master WHERE name='research_permissions'").fetchone()[0], 0)
        execution = self.db.execute('SELECT started,finished FROM executions').fetchone()
        self.assertEqual(execution['finished'] - execution['started'], 105)
