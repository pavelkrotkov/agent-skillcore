import json
from unittest.mock import patch
from x_batch_fixtures import BatchCase
from x_quick_fixtures import native
from x_curator import batch_report, quick_mcp, quick_sources, review_outbox, review_permissions
from x_curator.quick_final import FORMAT
from x_curator.receipts import digest


class ReadWindowTriageTests(BatchCase):
    def checker(self, request):
        source = quick_sources.source(self.db, self.token, 'https://example.test/article')
        with patch('time.time', return_value=request['deadline'] - 40):
            response = quick_mcp.call(self.db, self.token, 'read', {'source': source})
        self.assertTrue(response['isError'])
        decision = {'outcome': 'inconclusive', 'reason': 'The claim lacks evidence within the quick window.',
                    'central': ['c1'], 'checks': [{'id': 'c1', 'text': 'The central claim is true.',
                                                 'status': 'inconclusive', 'sources': []}]}
        accepted = quick_mcp.call(self.db, self.token, 'validate', {'decision': decision})
        self.assertFalse(accepted['isError'])
        return native(request, {'format': FORMAT, 'decision_sha': digest(decision)}, [response, accepted])

    def test_normal_cutoff_keeps_explicit_review_available_without_granting_research(self):
        self.run_batch()
        batch = batch_report.report(self.db)['batches'][0]
        self.assertEqual(batch['counts'], {'pending_decision': 1})
        self.assertEqual(batch['items'][0]['retrieval_failures'], [])
        delivery = review_outbox.prepare(self.db, batch['id'], 'synthetic-chat')
        item = json.loads(delivery['payload'])['review'][0]
        review_permissions.require_pending(self.db, 'synthetic-account', item, 'research')
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 0)
