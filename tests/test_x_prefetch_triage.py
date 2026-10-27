from x_linked_fixtures import LinkedCase
from x_curator import batch_report, review_outbox
from x_curator.quick_failures import MEDIA_REFUSAL
from x_curator.quick_window import READ_CLOSED


class PrefetchTriageTests(LinkedCase):
    def pending(self, _request):
        return dict(format='compact-v1', outcome='inconclusive', reason='The linked claim remains unresolved.', claims=[])

    def test_prefetch_access_failure_is_operator_work_not_a_research_request(self):
        self.fetch = lambda _: (_ for _ in ()).throw(OSError('synthetic DNS failure'))
        self.decision = self.pending
        self.run_worker()
        original = tuple(self.db.execute('SELECT * FROM quick_checks').fetchone())
        batch = batch_report.report(self.db)['batches'][0]
        self.assertEqual(batch['counts'], {'failed_processing': 1})
        self.assertEqual(batch['review'], [])
        self.assertIn('synthetic DNS failure', ' '.join(batch['items'][0]['retrieval_failures']))
        message = review_outbox.prepare(self.db, batch['id'], 'synthetic-chat')['message']
        self.assertIn('No research approval is requested by this digest.', message)
        self.assertEqual(tuple(self.db.execute('SELECT * FROM quick_checks').fetchone()), original)

    def test_intentional_media_scope_refusal_remains_a_content_decision(self):
        self.fetch = lambda _: (_ for _ in ()).throw(ValueError(MEDIA_REFUSAL))
        self.decision = self.pending
        self.run_worker()
        batch = batch_report.report(self.db)['batches'][0]
        self.assertEqual(batch['counts'], {'pending_decision': 1})

    def test_normal_prefetch_cutoff_remains_a_content_decision(self):
        self.fetch = lambda _: (_ for _ in ()).throw(ValueError(READ_CLOSED))
        self.decision = self.pending
        self.run_worker()
        batch = batch_report.report(self.db)['batches'][0]
        self.assertEqual(batch['counts'], {'pending_decision': 1})
        self.assertEqual(batch['items'][0]['retrieval_failures'], [])
