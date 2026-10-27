import time
from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_curator.deadlines import DeadlineExceeded, until
from x_curator.leases import claim, fail_owned
from x_curator.worker import process


class DeadlineTests(PublicationCase):
    def test_nested_network_limit_cannot_extend_attempt_deadline(self):
        start = time.monotonic()
        with self.assertRaises(DeadlineExceeded):
            with until(time.time() + 0.05):
                with until(time.time() + 10):
                    time.sleep(2)
        self.assertLess(time.monotonic() - start, 1)

    def test_expired_attempt_records_failure_without_escaping(self):
        with self.db:
            self.db.execute('UPDATE jobs SET lease_until=?', (time.time() - 1,))
        job = dict(self.db.execute('SELECT * FROM jobs').fetchone())
        with patch('x_curator.worker_process.research') as research:
            result = process(self.db, self.root, None, job)
        research.assert_not_called()
        self.assertEqual(result['state'], 'retry')
        self.assertIn('deadline', self.db.execute('SELECT action FROM attempts').fetchone()[0])

    def test_old_failure_cannot_modify_replacement_lease(self):
        with self.db:
            self.db.execute('UPDATE jobs SET lease_until=0')
            self.db.execute('UPDATE attempts SET expires=0')
        replacement = claim(self.db, 'synthetic-account')
        fail_owned(self.db, self.token, 'old deadline exhausted', 300)
        row = self.db.execute('SELECT token,state FROM jobs').fetchone()
        self.assertEqual(tuple(row), (replacement['token'], 'leased'))
