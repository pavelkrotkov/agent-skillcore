from unittest.mock import patch
from x_deep_fixtures import DeepCase
from x_curator import batch_queue, deep_claim, deep_review


class UnspentDeepRecoveryTests(DeepCase):
    def test_unspent_dispatch_retains_expired_approved_research_disposition(self):
        self.authorize()
        job = deep_claim.claim(self.db, self.approval)
        before = dict(self.db.execute('SELECT * FROM deep_runs').fetchone())
        attempts = self.db.execute('SELECT count(*) FROM attempts').fetchone()[0]
        with patch('x_curator.batch_queue.time.time', return_value=job['lease_until'] + 1):
            self.assertIsNone(batch_queue.claim(self.db, job['account'], unspent_only=True))
        after = dict(self.db.execute('SELECT * FROM deep_runs').fetchone())
        self.assertEqual('inconclusive', after['outcome'])
        self.assertEqual(attempts, self.db.execute('SELECT count(*) FROM attempts').fetchone()[0])
        for key in ('started', 'deadline', 'searches', 'token'):
            self.assertEqual(before[key], after[key])
        self.assertIsNotNone(deep_review.prepare(self.db, job['account'], 'synthetic-chat'))
