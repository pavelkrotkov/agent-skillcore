from unittest.mock import patch

from x_batch_fixtures import BatchCase
from x_curator import batch_report
from x_curator.publication_audit import audit


class BatchFlowTests(BatchCase):
    def test_multi_batch_cohort_publishes_without_deep_work(self):
        self.add_items(53)
        result = self.run_batch()
        batches = batch_report.report(self.db)['batches']
        self.assertEqual([len(b['items']) for b in batches], [50, 3])
        self.assertEqual([b['state'] for b in batches], ['closed', 'closed'])
        self.assertEqual(result['completed'], 53)
        self.assertEqual(audit(self.db, self.root), [])
        self.assertEqual(self.run_batch()['attempted'], 0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 53)

    def test_pending_decisions_do_not_block_later_batches(self):
        self.add_items(52)
        self.checker = self.pending
        self.run_batch()
        batches = batch_report.report(self.db)['batches']
        self.assertEqual([len(b['review']) for b in batches], [50, 2])
        self.assertEqual([b['counts'] for b in batches], [{'pending_decision': 50}, {'pending_decision': 2}])
        first = batches[0]['review'][0]
        self.assertEqual(first['seconds'], 600)
        self.assertIn('2025', first['question'])
        self.assertTrue(first['revision'])
        self.assertEqual(self.run_batch()['attempted'], 0)

    def test_infrastructure_failure_is_visible_not_a_completed_fact_check(self):
        def failed(_):
            raise OSError('synthetic source transport failure')
        self.fetch = failed
        self.run_batch()
        batch = batch_report.report(self.db)['batches'][0]
        self.assertEqual(batch['counts'], {'failed_processing': 1})
        self.assertEqual(batch['review'], [])
        self.assertIn('Quick check inconclusive', batch['items'][0]['reason'])

    def test_unavailable_optional_speech_service_does_not_gate_quick_work(self):
        with patch.dict('os.environ', {'X_CURATOR_SPEECH_CONFIG': str(self.root / 'missing-reader.json')}):
            self.assertEqual(self.run_batch()['completed'], 1)
