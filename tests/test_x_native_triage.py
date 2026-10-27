import json

import test_x_retrieval_triage
from x_curator import batch_report, native_search, review_outbox
from x_curator.receipts import digest, encoded


class NativeTriageTests(test_x_retrieval_triage.RetrievalTriageTests):
    search_mode = native_search.MODE

    def checker(self, request):
        event = encoded({'type': 'item.completed', 'item': {'id': 'native-search', 'type': 'web_search',
                        'action': {'type': 'search', 'query': 'synthetic primary source'},
                        'results': [{'url': 'https://example.test/article'}]}}) + b'\n'
        root = self.root / 'runs' / self.token
        root.mkdir(parents=True)
        (root / (digest(request) + '.jsonl')).write_bytes(event)
        proof = json.loads(super().checker(request))
        proof['events'] = event.decode() + proof['events']
        return encoded(proof)

    def test_unfinished_native_search_cannot_create_a_research_proposal(self):
        original = self.checker
        def interrupted(request):
            proof = json.loads(original(request))
            proof['events'] += '\n' + json.dumps({'type': 'item.started', 'item': {
                'id': 'interrupted', 'type': 'web_search', 'action': {'type': 'other'}}})
            return encoded(proof)
        self.checker = interrupted
        self.run_batch()
        batch = batch_report.report(self.db)['batches'][0]
        self.assertEqual(batch['counts'], {'failed_processing': 1})
        self.assertEqual(batch['review'], [])
        message = review_outbox.prepare(self.db, batch['id'], 'synthetic-chat')['message']
        self.assertIn('No research approval is requested by this digest.', message)
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 0)
