import json
from x_native_search_fixtures import NativeCase
from x_curator import native_search_trace
from x_curator.receipts import encoded


class NativeProofTests(NativeCase):
    def test_removed_result_from_final_receipt_cannot_support_publication(self):
        original = self.checker
        def checker(request):
            proof = json.loads(original(request))
            rows = [json.loads(line) for line in proof['events'].splitlines()]
            rows[0]['item']['results'] = []
            proof['events'] = '\n'.join(json.dumps(row) for row in rows)
            return encoded(proof)
        self.checker = checker
        self.assertIsNone(self.run_check())
        self.assertIn('read URL absent', self.db.execute('SELECT reason FROM quick_checks').fetchone()[0])

    def test_nonsearch_action_cannot_register_a_url(self):
        item = json.loads(self.search_log)
        item['item']['action'] = {'type': 'open_page', 'url': 'https://example.test/release'}
        self.assertEqual(native_search_trace.urls(encoded(item)), set())

    def test_redirected_body_remains_bound_to_original_search_result_url(self):
        original = self.fetch
        self.fetch = lambda url: (302, 'text/html', b'', 'https://example.test/final') if url.endswith('/release') else original(url)
        self.assertIsNotNone(self.run_check())
        self.assertEqual(self.calls, ['https://example.test/final'])
