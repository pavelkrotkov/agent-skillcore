import json

from x_native_search_fixtures import NativeCase
from x_curator import policy_metrics, quick_mcp
from x_curator.publication_audit import audit
from x_curator.codex_runner import arguments
from x_curator.worker_prompts import prompt


class NativeSearchTests(NativeCase):
    def test_four_actual_queries_publish_with_body_proof_and_preserve_history(self):
        identity = self.run_check()
        self.assertIsNotNone(identity)
        self.assertEqual(audit(self.db, self.root), [])
        metrics = policy_metrics.report(self.db)
        self.assertEqual(metrics['runs'][0]['overruns'], [])
        self.assertIsNone(metrics['runs'][0]['search_limit'])
        check = self.db.execute('SELECT * FROM quick_checks').fetchone()
        self.assertEqual(check['searches'], 4)
        self.assertEqual(check['deadline'] - check['started'], 120)
        self.assertEqual(self.calls, ['https://example.test/release'])
        with self.db:
            self.db.execute('UPDATE quick_checks SET searches=3')
        self.assertEqual(audit(self.db, self.root), [identity])

    def test_only_search_result_urls_are_admitted_and_curator_search_is_disabled(self):
        original = self.checker
        def checker(request):
            result = original(request)
            self.assertTrue(quick_mcp.call(self.db, self.token, 'read', {'source': 'https://example.test/invented'})['isError'])
            self.assertTrue(quick_mcp.call(self.db, self.token, 'search', {'query': 'bypass'})['isError'])
            tools = quick_mcp.respond(self.db, self.token, {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})
            self.assertEqual({t['name'] for t in tools['tools']}, {'read', 'validate'})
            return result
        self.checker = checker
        self.run_check()
        self.assertEqual(self.calls, ['https://example.test/release'])
        self.assertEqual(self.db.execute('SELECT searches FROM quick_checks').fetchone()[0], 4)

    def test_unfinished_native_call_prevents_publication(self):
        self.search_log += b'{"type":"item.started","item":{"type":"web_search","id":"unfinished","action":{"type":"other"}}}\n'
        self.assertIsNone(self.run_check())
        self.assertIn('usage', self.db.execute('SELECT reason FROM quick_checks').fetchone()[0])

    def test_profile_routes_only_new_quick_checks_to_native_search(self):
        self.run_check()
        request = json.loads(self.db.execute('SELECT input FROM executions').fetchone()[0])
        native_args = arguments(self.db, self.root / self.token, 'codex', request)
        self.assertIn('web_search="live"', native_args)
        self.assertIn('mcp_servers.curator.enabled_tools=["read", "validate"]', native_args)
        self.assertIn("format:'compact-v1'", prompt(request))
        self.assertIn('target', prompt(request))
        legacy = dict(request, policy='approved-deep/v1')
        self.assertIn('web_search="disabled"', arguments(self.db, self.root / self.token, 'codex', legacy))
        self.assertNotIn('This is a target', prompt(legacy))
