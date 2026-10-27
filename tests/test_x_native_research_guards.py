import json

from x_native_research_fixtures import NativeDeepCase
from x_quick_fixtures import native
from x_curator import native_search, quick_mcp
from x_curator.receipts import encoded
from x_curator.model_events import result as model_result


class NativeResearchGuardTests(NativeDeepCase):
    def test_native_research_rejects_unobserved_urls_and_legacy_search(self):
        self.native_approval()
        original = self.checker
        def checker(request):
            result = original(request)
            self.tools.extend([quick_mcp.call(self.db, self.token, 'read', {'source': 'https://example.test/invented'}),
                               quick_mcp.call(self.db, self.token, 'search', {'query': 'bypass'})])
            self.assertTrue(all(v['isError'] for v in self.tools[-2:]))
            return native(request, model_result(result)[1], self.tools, self.search_log)
        self.checker = checker
        self.assertEqual(self.deep()['state'], 'published')
        self.assertEqual(self.calls, ['https://example.test/release'])

    def test_unfinished_native_search_cannot_publish(self):
        self.native_approval()
        self.search_log += encoded({'type': 'item.started', 'item': {'type': 'web_search', 'id': 'unfinished', 'action': {'type': 'other'}}}) + b'\n'
        self.assertEqual(self.deep()['state'], 'awaiting_review')
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)

    def test_native_mode_requires_matching_immutable_permission(self):
        self.authorize()
        from x_curator.deep_proof import require_request
        from x_curator.deep_permission import verified
        from x_curator.evidence import bundle, capture_selection
        from x_curator.deep_claim import claim
        job = claim(self.db, self.approval)
        capture_selection(self.db, job['token'])
        permission, proposal = verified(self.db, self.approval)
        request = dict(job, bundle=bundle(self.db, job['token']), resource=None, search_mode=native_search.RESEARCH_MODE)
        with self.assertRaisesRegex(ValueError, 'outside'):
            require_request(dict(id=self.approval, deadline=job['deadline']), permission, proposal, request)
