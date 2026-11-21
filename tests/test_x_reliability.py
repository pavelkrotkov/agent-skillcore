"""Regression cases for idle writer contention and technical retry dispatch."""
from unittest.mock import patch

from x_fixtures import Client
from x_quick_fixtures import QuickCase
from x_curator import provider_health, quick_process, review_reconcile, review_store
from x_curator.queue import enqueue
from x_curator.storage import open_store


class ReliabilityTests(QuickCase):
    def test_technical_verification_failure_schedules_a_bounded_retry(self):
        with patch('x_curator.quick_process.runner', side_effect=OSError('synthetic transport interruption')):
            quick_process.research(self.db, self.root, self.client, self.token)
        job = self.db.execute('SELECT * FROM jobs').fetchone()
        self.assertEqual(job['state'], 'retry')
        self.assertEqual((job['attempts'], job['max_attempts']), (1, 3))
        self.assertGreater(job['next_at'], 0)

    def test_idle_queue_and_delivery_status_do_not_compete_with_an_existing_writer(self):
        enqueue(self.db)
        review_store.initialize(self.db)
        provider_health.initialize(self.db)
        with self.db:
            self.db.execute('INSERT INTO review_routes VALUES (?,?)', (Client.account, 'synthetic-chat'))
            self.db.executemany("INSERT INTO curation_batches VALUES (?,?,'daily',?,?,'closed')",
                                [('empty-' + str(i), Client.account, i, i) for i in range(16)])
        other = open_store(self.root)
        try:
            other.execute('BEGIN IMMEDIATE')
            self.db.execute('PRAGMA busy_timeout=20')
            enqueue(self.db)
            self.assertIsNone(provider_health.blocked(self.db))
            self.assertEqual(review_reconcile.flush(self.db, Client.account), [])
        finally:
            other.rollback()
            other.close()
