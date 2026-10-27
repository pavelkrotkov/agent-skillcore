from x_deep_fixtures import DeepCase
from x_curator import batch_queue, deep_claim, deep_review, quick_store
from x_curator.deadlines import DeadlineExceeded
from x_curator.queue import recover
from x_curator.storage import open_store


class DeepRecoveryTests(DeepCase):
    def test_timeout_is_unresolved_with_spent_permission_and_no_automatic_retry(self):
        self.authorize()
        self.checker = lambda request: (_ for _ in ()).throw(DeadlineExceeded('Synthetic timeout'))
        self.assertEqual(self.deep()['state'], 'awaiting_review')
        self.assertIsNotNone(self.db.execute('SELECT consumed FROM research_permissions').fetchone()[0])
        with self.assertRaises(ValueError):
            self.deep()
        self.assertEqual(self.run_batch()['attempted'], 0)

    def test_restart_recovers_expired_deep_lease_to_review_without_refilling_budget(self):
        self.authorize()
        job = deep_claim.claim(self.db, self.approval)
        token = job['token']
        for _ in range(12):
            quick_store.reserve_search(self.db, token)
        with self.assertRaises(ValueError):
            quick_store.reserve_search(self.db, token)
        before = dict(self.db.execute('SELECT * FROM deep_runs').fetchone())
        self.db.close()
        self.db = open_store(self.root)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            recover(self.db, job['account'], job['lease_until'] + 1)
        after = dict(self.db.execute('SELECT * FROM deep_runs').fetchone())
        for key in ('started', 'deadline', 'searches', 'id', 'token'):
            self.assertEqual(after[key], before[key])
        self.assertEqual(after['outcome'], 'inconclusive')
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'awaiting_review')
        self.assertIsNotNone(deep_review.prepare(self.db, job['account'], 'synthetic-chat'))
        self.assertIsNone(deep_review.prepare(self.db, job['account'], 'synthetic-chat'))
        with self.assertRaises(ValueError):
            deep_claim.claim(self.db, self.approval)

    def test_capacity_refusal_does_not_spend_approval_and_deep_occupies_a_shared_slot(self):
        self.authorize()
        self.add_items(4)
        account = self.db.execute('SELECT account FROM jobs LIMIT 1').fetchone()[0]
        first = batch_queue.claim(self.db, account)
        second = batch_queue.claim(self.db, account)
        self.assertIsNone(deep_claim.claim(self.db, self.approval))
        self.assertIsNone(self.db.execute('SELECT consumed FROM research_permissions').fetchone()[0])
        with self.db:
            recover(self.db, account, max(first['lease_until'], second['lease_until']) + 1)
        deep_claim.claim(self.db, self.approval)
        self.assertIsNotNone(batch_queue.claim(self.db, account))
        self.assertIsNone(batch_queue.claim(self.db, account))
