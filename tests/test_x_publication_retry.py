import sqlite3
from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_curator.deadlines import DeadlineExceeded
from x_curator.publication import publish
from x_curator.verdicts import approved


class PublicationRetryTests(PublicationCase):
    def test_deadlines_and_other_database_errors_do_not_retry(self):
        proposal, review = self.approved_executions()
        for error in (DeadlineExceeded('expired'), sqlite3.OperationalError('other database error')):
            with self.subTest(error=type(error).__name__), patch('x_curator.publication.approved', side_effect=error) as verify:
                with self.assertRaises(type(error)):
                    publish(self.db, self.root, self.token, proposal, review)
                verify.assert_called_once()
        self.assertFalse(self.db.in_transaction)
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)

    def test_snapshot_retry_rechecks_lease_before_any_publication(self):
        proposal, review = self.approved_executions()
        other = sqlite3.connect(self.root / 'curator.sqlite3', timeout=0.05)
        def expire(*args):
            packet = approved(*args)
            with other:
                other.execute('UPDATE jobs SET lease_until=0')
            return packet
        try:
            with patch('x_curator.publication.approved', side_effect=expire) as verify:
                with self.assertRaisesRegex(ValueError, 'expired or superseded'):
                    publish(self.db, self.root, self.token, proposal, review)
                self.assertEqual(verify.call_count, 2)
        finally:
            other.close()
        self.assertFalse(self.db.in_transaction)
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM executions').fetchone()[0], 2)
