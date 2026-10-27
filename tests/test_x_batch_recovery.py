import time

from x_batch_fixtures import BatchCase
from x_fixtures import Client
from x_curator import batch_queue, batch_report, quick_store
from x_curator.storage import open_store
from x_curator.leases import fail


class BatchRecoveryTests(BatchCase):
    def test_overlapping_dispatch_keeps_one_cohort_and_distinct_leases(self):
        self.add_items(51)
        first = batch_queue.claim(self.db, Client.account)
        other = open_store(self.root)
        try:
            second = batch_queue.claim(other, Client.account)
            self.assertEqual(first['batch'], second['batch'])
            self.assertNotEqual(first['id'], second['id'])
            self.assertEqual(other.execute('SELECT count(*) FROM curation_members').fetchone()[0], 50)
        finally:
            other.close()

    def test_restart_preserves_member_reference_deadline_and_query_budget(self):
        first = batch_queue.claim(self.db, Client.account)
        check = quick_store.start(self.db, first['token'], time.time())
        quick_store.reserve_search(self.db, first['token'])
        reference = batch_report.report(self.db)['batches'][0]['items'][0]['reference']
        fail(self.db, first['token'], 'Synthetic interruption', 0)
        self.db.close()
        self.db = open_store(self.root)
        resumed = batch_queue.claim(self.db, Client.account)
        again = quick_store.start(self.db, resumed['token'], time.time())
        self.assertEqual((check['deadline'], 1), (again['deadline'], again['searches']))
        self.assertEqual(first['batch'], resumed['batch'])
        self.assertEqual(reference, batch_report.report(self.db)['batches'][0]['items'][0]['reference'])

    def test_deferred_retry_does_not_hold_ready_items_behind_its_batch(self):
        self.add_items(51)
        first = batch_queue.claim(self.db, Client.account)
        fail(self.db, first['token'], 'Synthetic delayed retry', 3600)
        self.checker = self.pending
        result = self.run_batch()
        batches = batch_report.report(self.db)['batches']
        self.assertEqual(result['attempted'], 50)
        self.assertEqual([len(b['items']) for b in batches], [50, 1])
        self.assertEqual([b['state'] for b in batches], ['open', 'closed'])
        self.assertEqual(batches[0]['counts'], {'processing': 1, 'pending_decision': 49})
