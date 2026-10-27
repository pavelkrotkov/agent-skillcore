import json
from unittest.mock import patch

from x_prepared_fixtures import PreparedCase
from x_curator.publication_recovery import complete
from x_curator.publication_audit import verify_publication


class PreparedRecoveryTests(PreparedCase):
    def test_completion_preserves_failed_attempt_and_budgets_and_is_idempotent(self):
        with patch('x_curator.research.runner', side_effect=AssertionError('no model calls')):
            result = complete(self.db, self.root, self.identity, 'Verified prepared source after commit fix')
            repeated = complete(self.db, self.root, self.identity, 'Repeated operator request')
        self.assertFalse(result['already_completed'])
        self.assertTrue(repeated['already_completed'])
        self.assertEqual(self.ledger(), self.before)
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'published')
        records = self.db.execute('SELECT receipt FROM publication_recoveries').fetchall()
        self.assertEqual(len(records), 1)
        self.assertEqual(json.loads(records[0][0])['prior_job']['state'], 'retry')
        verify_publication(self.db, self.root, self.db.execute('SELECT * FROM publications').fetchone())

    def test_exhausted_source_needs_no_new_attempt_grant(self):
        with self.db:
            self.db.execute("UPDATE jobs SET state='needs_action',attempts=max_attempts")
        before = self.ledger()
        complete(self.db, self.root, self.identity, 'Finish approved evidence')
        self.assertEqual(self.ledger(), before)
        self.assertEqual(self.db.execute('SELECT count(*) FROM executions').fetchone()[0], 2)

    def test_completed_receipt_cannot_be_reused_as_new_preparation(self):
        complete(self.db, self.root, self.identity, 'Finish approved evidence once')
        with self.db:
            self.db.execute("UPDATE publications SET state='prepared'")
            self.db.execute("UPDATE jobs SET state='retry'")
        with self.assertRaisesRegex(ValueError, 'eligible'):
            complete(self.db, self.root, self.identity, 'Historical completion is not a new preparation')
        self.assertEqual(self.ledger(), self.before)

    def test_tampered_file_or_receipt_never_completes_silently(self):
        target = self.root / self.row['path']
        target.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'differs'):
            complete(self.db, self.root, self.identity, 'Must reject corrupted page')
        self.assertEqual(self.db.execute('SELECT count(*) FROM publication_recoveries').fetchone()[0], 0)
        target.write_bytes(self.row['body'])
        complete(self.db, self.root, self.identity, 'Verified restored bytes')
        with self.db:
            self.db.execute("UPDATE publication_recoveries SET receipt='{}'")
        with self.assertRaisesRegex(ValueError, 'tampered'):
            complete(self.db, self.root, self.identity, 'Must reject corrupt recovery')
