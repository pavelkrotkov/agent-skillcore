from x_batch_fixtures import BatchCase
from x_curator import batch_report, review_outbox


class BatchDigestTests(BatchCase):
    def test_one_mixed_result_preserves_exclusions_and_distinguishes_failures(self):
        self.add_items(5)
        original = self.checker
        def disprove(value):
            value['checks'][0]['status'] = 'disproven'
            value.update(outcome='disproven', reason='The primary evidence disproves the central claim.')
            value.pop('packet')
            return value
        def mixed(request):
            source = request['bundle']['source']
            if source in ('3', '5'):
                return self.pending(request)
            if source == '4':
                raise OSError('Synthetic model transport interruption')
            self.modify = disprove if source == '2' else lambda value: value
            return original(request)
        self.checker = mixed
        self.run_batch()
        batch = batch_report.report(self.db)['batches'][0]
        self.assertEqual(batch['counts'], {'supported': 1, 'excluded': 1, 'pending_decision': 2, 'failed_processing': 1})
        self.assertEqual({i['source'] for i in batch['review']}, {'3', '5'})
        message = review_outbox.prepare(self.db, batch['id'], 'synthetic-chat')['message']
        self.assertIn('Status: useful notes 1; completed factual checks 4; technical failures 1; still processing 0.', message)
        self.assertIn('Research questions requiring explicit approval:', message)
        self.assertIn('Technical failures (not research approval):', message)
        self.assertIn(batch['id'] + ':4', message)

    def test_later_processing_failure_cannot_reuse_stale_pending_decision(self):
        self.checker = self.pending
        self.run_batch()
        with self.db:
            self.db.execute("UPDATE jobs SET action='Publication proof needs repair'")
        batch = batch_report.report(self.db)['batches'][0]
        self.assertEqual(batch['review'], [])
        self.assertEqual(batch['counts'], {'failed_processing': 1})
        self.assertEqual(batch['items'][0]['reason'], 'Publication proof needs repair')
        message = review_outbox.prepare(self.db, batch['id'], 'synthetic-chat')['message']
        self.assertIn('Technical failures (not research approval):', message)
        self.assertIn('No research approval is requested by this digest.', message)
