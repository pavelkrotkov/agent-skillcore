from unittest.mock import patch

from x_daily_fixtures import DailyCase
from x_curator import batch_queue, batch_report, review_reconcile
from x_curator.leases import fail
from x_curator.storage import open_store
from x_fixtures import Client


class DailyRecoveryTests(DailyCase):
    def test_frozen_empty_cutoff_does_not_absorb_late_recorded_arrivals(self):
        self.daily_work()
        self.intake([2], self.cutoff - 1)
        self.assertEqual(self.daily_work()['attempted'], 0)
        self.db.close()
        self.db = open_store(self.root)
        self.cutoff += 86400
        self.assertEqual(self.daily_work()['completed'], 1)
        daily = [b for b in batch_report.report(self.db)['batches'] if b['kind'] == 'daily']
        self.assertEqual([len(b['items']) for b in daily], [0, 1])

    def test_delayed_daily_retry_does_not_block_backlog_and_reconciliation_survives_restart(self):
        self.intake([2], self.baseline + 10)
        with patch('x_curator.daily_plan.cutoff', return_value=self.cutoff):
            job = batch_queue.claim(self.db, Client.account)
        self.assertEqual(job['id'], '2')
        fail(self.db, job['token'], 'Synthetic delayed daily retry', 3600)
        self.checker = self.pending
        with patch('x_curator.worker.flush', return_value=[]):
            self.assertEqual(self.daily_work()['attempted'], 1)
        self.db.close()
        self.db = open_store(self.root)
        result = review_reconcile.flush(self.db, Client.account)
        self.assertEqual(len([r for r in result if r.get('delivery')]), 1)
        self.assertEqual(review_reconcile.flush(self.db, Client.account), [])
