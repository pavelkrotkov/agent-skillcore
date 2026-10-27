import time
from unittest.mock import patch

from x_finalization_feedback_fixtures import FeedbackCase
from x_curator.publication_audit import audit


class FinalizationFeedbackTests(FeedbackCase):
    def run_timed(self, subjective):
        self.subjective = subjective
        self.start = self.at = time.time()
        with patch('time.time', side_effect=lambda: self.at):
            self.assertIsNotNone(self.run_final())
            self.assertEqual(audit(self.db, self.root), [])
        check = self.db.execute('SELECT * FROM quick_checks').fetchone()
        self.assertEqual(check['deadline'] - check['started'], 120)
        self.assertEqual(self.db.execute('SELECT count(*) FROM attempts').fetchone()[0], 1)
        execution = self.db.execute('SELECT started,finished FROM executions').fetchone()
        self.assertEqual(execution['finished'] - execution['started'], 100)

    def test_factual_capture_typo_corrects_and_finalizes_in_same_attempt(self):
        self.run_timed(False)

    def test_subjective_capture_typo_corrects_and_finalizes_in_same_attempt(self):
        self.run_timed(True)
