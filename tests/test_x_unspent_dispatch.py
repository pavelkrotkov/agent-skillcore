import time
from unittest.mock import patch
from x_batch_fixtures import BatchCase
from x_fixtures import Client
from x_curator import batch_queue, batch_selection, quick_store
from x_curator.leases import fail


class UnspentDispatchTests(BatchCase):
    def crash(self, check):
        self.add_items(2)
        first = batch_queue.claim(self.db, Client.account, unspent_only=True)
        if check:
            receipt = quick_store.start(self.db, first['token'], time.time())
        attempts = self.db.execute('SELECT count(*) FROM attempts').fetchone()[0]
        with patch('x_curator.batch_queue.time.time', return_value=first['lease_until'] + 1):
            self.assertIsNone(batch_queue.claim(self.db, Client.account, unspent_only=True))
        self.assertEqual(attempts, self.db.execute('SELECT count(*) FROM attempts').fetchone()[0])
        self.assertEqual('needs_action', self.db.execute('SELECT state FROM jobs WHERE id=?', (first['id'],)).fetchone()[0])
        self.assertEqual('expired', self.db.execute('SELECT state FROM attempts WHERE token=?', (first['token'],)).fetchone()[0])
        if check:
            self.assertEqual(dict(self.db.execute('SELECT * FROM quick_checks WHERE token=?', (first['token'],)).fetchone()), receipt)
        else:
            self.assertFalse(self.db.execute('SELECT 1 FROM quick_checks WHERE token=?', (first['token'],)).fetchone())

    def test_crash_before_allowance_cannot_grant_a_second_attempt(self):
        self.crash(False)

    def test_crash_after_allowance_preserves_original_deadline_without_retokening(self):
        self.crash(True)

    def test_held_spent_members_do_not_starve_next_unspent_batch(self):
        self.add_items(52)
        first = batch_queue.claim(self.db, Client.account, unspent_only=True)
        fail(self.db, first['token'], 'Synthetic interruption', 0)
        last = self.db.execute('SELECT id FROM jobs j WHERE NOT EXISTS (SELECT 1 FROM curation_members m WHERE m.account=j.account AND m.source=j.id) ORDER BY created,id LIMIT 1').fetchone()[0]
        with self.db:
            self.db.execute("UPDATE jobs SET state='awaiting_review' WHERE attempts=0 AND id!=?", (last,))
        self.assertIsNone(batch_selection.ready(self.db, Client.account, time.time(), 'backlog', True))
        next_job = batch_queue.claim(self.db, Client.account, unspent_only=True)
        self.assertEqual(last, next_job['id'])
        self.assertNotEqual(first['batch'], next_job['batch'])
        self.assertEqual(1, next_job['attempts'])

    def test_no_spent_pending_member_is_eligible(self):
        first = batch_queue.claim(self.db, Client.account)
        with self.db:
            self.db.execute("UPDATE jobs SET state='pending',token=NULL,lease_until=NULL WHERE token=?", (first['token'],))
            self.db.execute("UPDATE attempts SET state='failed',finished=? WHERE token=?", (time.time(), first['token']))
        self.assertIsNone(batch_queue.claim(self.db, Client.account, unspent_only=True))
        self.assertEqual(first['attempts'], self.db.execute('SELECT attempts FROM jobs WHERE id=?', (first['id'],)).fetchone()[0])
