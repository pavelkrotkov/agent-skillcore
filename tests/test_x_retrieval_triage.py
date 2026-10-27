import json
from unittest.mock import patch

from x_batch_fixtures import BatchCase
from x_quick_fixtures import native
from x_curator import batch_report, quick_mcp, quick_sources, review_outbox, review_permissions


class RetrievalTriageTests(BatchCase):
    def checker(self, request):
        source = quick_sources.source(self.db, self.token, 'https://example.test/article')
        result = quick_mcp.call(self.db, self.token, 'read', {'source': source})
        decision = {'outcome': 'inconclusive', 'reason': 'The central claim lacks accessible evidence.',
                    'central': ['c1'], 'checks': [{'id': 'c1', 'text': 'The central claim is true.',
                                                 'status': 'inconclusive', 'sources': []}]}
        return native(request, decision, [result])

    def test_failed_retrieval_is_not_a_human_research_request(self):
        self.fetch = lambda url: (403, 'text/html', b'Forbidden', None)
        self.run_batch()
        original = dict(self.db.execute('SELECT * FROM quick_checks').fetchone())
        batch = batch_report.report(self.db)['batches'][0]
        self.assertEqual(batch['counts'], {'failed_processing': 1})
        self.assertEqual(batch['review'], [])
        self.assertIn('HTTP 403', batch['items'][0]['retrieval_failures'][0])
        message = review_outbox.prepare(self.db, batch['id'], 'synthetic-chat')['message']
        self.assertIn('Technical failures (not research approval):', message)
        self.assertIn('No research approval is requested by this digest.', message)
        self.assertEqual(dict(self.db.execute('SELECT * FROM quick_checks').fetchone()), original)

    def test_explicit_media_scope_limit_can_still_request_human_research(self):
        self.fetch = lambda url: (200, 'application/pdf', b'%PDF synthetic', None)
        self.run_batch()
        batch = batch_report.report(self.db)['batches'][0]
        self.assertEqual(batch['counts'], {'pending_decision': 1})
        self.assertIsNotNone(review_outbox.prepare(self.db, batch['id'], 'synthetic-chat'))

    def test_frozen_request_cannot_grant_research_after_classification_changes(self):
        self.fetch = lambda url: (403, 'text/html', b'Forbidden', None)
        self.run_batch()
        with patch('x_curator.batch_report.quick_failures.retrieval', return_value=[]):
            batch = batch_report.report(self.db)['batches'][0]
            delivery = review_outbox.prepare(self.db, batch['id'], 'synthetic-chat')
        item = json.loads(delivery['payload'])['review'][0]
        original = delivery['message']
        with self.db:
            with self.assertRaisesRegex(ValueError, 'operator triage'):
                review_permissions.decide(self.db, delivery, item, 'research', 'synthetic-message')
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM review_decisions').fetchone()[0], 0)
        self.assertEqual(review_outbox.prepare(self.db, batch['id'], 'synthetic-chat')['message'], original)

    def test_malformed_retained_error_receipt_does_not_break_batch_or_request_research(self):
        self.fetch = lambda url: (403, 'text/html', b'Forbidden', None)
        self.run_batch()
        for corrupt in ('not JSON', '{"isError":true,"content":[]}', '{"isError":true,"content":[{"text":42}]}'):
            with self.subTest(receipt=corrupt), self.db:
                self.db.execute("UPDATE quick_tools SET output=? WHERE name='read'", (corrupt,))
                batch = batch_report.report(self.db)['batches'][0]
                self.assertEqual(batch['counts'], {'failed_processing': 1})
                self.assertIn('malformed acquisition receipt', batch['items'][0]['retrieval_failures'][0])
                self.assertEqual(batch['review'], [])
