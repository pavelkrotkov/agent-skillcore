from x_batch_fixtures import BatchCase
from x_quick_fixtures import native
from x_curator import batch_report, review_outbox


class CompactBatchTests(BatchCase):
    def test_compact_uncertainty_becomes_one_proposal_without_research(self):
        reason = 'Which original evidence establishes the synthetic release year?'
        self.checker = lambda request: native(request, {'format': 'compact-v1',
            'outcome': 'inconclusive', 'reason': reason, 'claims': []}, [])
        self.run_batch()
        batch = batch_report.report(self.db)['batches'][0]
        self.assertEqual(batch['counts'], {'pending_decision': 1})
        self.assertEqual(batch['review'][0]['question'], 'Check: ' + reason)
        value = review_outbox.prepare(self.db, batch['id'], 'synthetic-chat')
        self.assertIn(reason, value['message'])
        self.assertEqual(review_outbox.prepare(self.db, batch['id'], 'synthetic-chat'), value)
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 0)
