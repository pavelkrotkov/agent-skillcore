import json

from x_native_research_fixtures import NativeDeepCase
from x_curator import native_search, quick_mcp
from x_curator.codex_runner import arguments
from x_curator.publication_audit import audit
from x_curator.worker_prompts import prompt


class NativeResearchTests(NativeDeepCase):
    def test_explicit_native_scope_publishes_body_proof_and_records_actual_queries(self):
        self.native_approval()
        original = dict(self.db.execute('SELECT * FROM quick_checks').fetchone())
        self.assertEqual(self.deep()['state'], 'published')
        self.assertEqual(audit(self.db, self.root), [])
        run = self.db.execute('SELECT * FROM deep_runs WHERE id=?', (self.approval,)).fetchone()
        self.assertEqual(run['searches'], 13)
        self.assertEqual(run['deadline'] - run['started'], 600)
        self.assertEqual(dict(self.db.execute('SELECT * FROM quick_checks').fetchone()), original)
        request = json.loads(self.db.execute('SELECT input FROM executions WHERE token=?', (run['token'],)).fetchone()[0])
        args = arguments(self.db, self.root / run['token'], 'codex', request)
        self.assertIn('web_search="live"', args)
        self.assertIn('mcp_servers.curator.enabled_tools=["read", "validate"]', args)
        self.assertIn('This is a target', prompt(request))
        self.assertNotIn('excerpts remain the only interactive tools', prompt(request))
        with self.db:
            self.db.execute('UPDATE deep_runs SET searches=12 WHERE id=?', (self.approval,))
        self.assertTrue(audit(self.db, self.root))
