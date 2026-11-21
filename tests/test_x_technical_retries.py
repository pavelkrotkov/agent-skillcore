"""Finite retries preserve original receipts and hold substantive decisions."""
import time
from unittest.mock import patch

from x_fixtures import Client
from x_quick_fixtures import native
from x_retry_fixtures import RetryCase
from x_curator import batch_queue, quick_process, quick_store
from x_curator.storage import open_store


class TechnicalRetryTests(RetryCase):
    def test_retry_can_publish_after_restart_without_rewriting_original_receipts(self):
        quick_store.start(self.db, self.token, time.time())
        quick_store.reserve_search(self.db, self.token)
        old = self.failed()
        self.db.close()
        self.db = open_store(self.root)
        self.assertEqual(self.next_attempt()['attempts'], 2)
        with patch('x_curator.quick_process.runner', return_value=self.checker), \
                patch('x_curator.quick_search.fetch', self.fetch), patch('x_curator.quick_web.fetch', self.fetch):
            self.assertIsNotNone(quick_process.research(self.db, self.root, self.client, self.token))
        original = dict(self.db.execute('SELECT * FROM quick_checks WHERE id=?', (old['id'],)).fetchone())
        self.assertEqual(original, old)
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'published')
        self.assertEqual(self.db.execute('SELECT count(*) FROM quick_checks').fetchone()[0], 2)
        self.assertEqual(self.db.execute('SELECT count(*) FROM recovery_grants').fetchone()[0], 0)

    def test_three_total_attempts_exhaust_without_resetting_earlier_allowances(self):
        records = []
        for attempt in range(1, 4):
            if attempt > 1:
                self.next_attempt()
            records.append(self.failed())
        job = self.db.execute('SELECT * FROM jobs').fetchone()
        self.assertEqual((job['state'], job['attempts'], job['max_attempts']), ('needs_action', 3, 3))
        with patch('x_curator.batch_queue.time.time', return_value=job['next_at'] + 1):
            self.assertIsNone(batch_queue.claim(self.db, Client.account))
        self.assertEqual([dict(row) for row in self.db.execute('SELECT * FROM quick_checks ORDER BY started')], records)
        self.assertEqual(self.db.execute('SELECT count(*) FROM quick_retry_failures').fetchone()[0], 3)
        self.assertEqual(self.db.execute('SELECT count(*) FROM quick_recoveries').fetchone()[0], 2)

    def test_completed_factual_inconclusive_does_not_automatically_retry(self):
        decision = dict(outcome='inconclusive', reason='The release year remains unresolved.', central=['f1'],
                        checks=[dict(id='f1', text='The release was in 2025.', status='inconclusive', sources=[])])
        with patch('x_curator.quick_process.runner', return_value=lambda request: native(request, decision, [])):
            quick_process.research(self.db, self.root, self.client, self.token)
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'awaiting_review')
        self.assertEqual(self.db.execute('SELECT count(*) FROM quick_retry_failures').fetchone()[0], 0)
        self.assertIsNone(batch_queue.claim(self.db, Client.account))
