import json

from x_linked_fixtures import LinkedCase
from x_curator import accounting
from x_curator.codex_runner import arguments
from x_curator.deadlines import DeadlineExceeded


class LinkedFlowTests(LinkedCase):
    def test_linked_compact_verdict_publishes_through_ordinary_worker(self):
        result = self.run_worker()
        self.assertEqual(result['completed'], 1)
        self.assertFalse(self.validation['isError'])
        profile = arguments(self.db, self.root / self.token, 'codex', self.request)
        self.assertIn('web_search="live"', profile)
        self.assertIn('mcp_servers.curator.enabled_tools=["read", "validate"]', profile)
        output = json.loads(self.db.execute('SELECT output FROM executions').fetchone()[0])
        self.assertNotIn('id', output['claims'][0])
        body = self.db.execute('SELECT body FROM publications').fetchone()[0].decode()
        self.assertIn('## c1', body)
        self.assertEqual(accounting.report(self.db, self.root)['counts']['published'], 1)

    def test_foreign_selection_quote_cannot_support_fact(self):
        def foreign(request):
            decision = self.supported(request)
            selection, _ = self.ids(request)
            decision['claims'][0] = self.source(selection, 'I recommend the tool.')
            return decision
        self.decision = foreign
        result = self.run_worker()
        self.assertTrue(self.validation['isError'])
        self.assertEqual(result['results'][0]['state'], 'awaiting_review')
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)

    def test_disproven_central_premise_is_excluded(self):
        def disproven(request):
            _, linked = self.ids(request)
            claim = self.source(linked, 'The tool was released in 2025.', 'disproven')
            claim['text'] = 'The tool was released in 2024.'
            return {'format': 'compact-v1', 'outcome': 'disproven', 'reason': 'The primary source contradicts the year.',
                    'claims': [claim]}
        self.decision = disproven
        result = self.run_worker()
        self.assertFalse(self.validation['isError'])
        self.assertEqual(result['results'][0]['state'], 'excluded')

    def test_interrupted_linked_run_never_publishes(self):
        def interrupted(_db, token):
            self.token = token
            return lambda _request: (_ for _ in ()).throw(DeadlineExceeded('synthetic interruption'))
        result = self.run_worker(interrupted)
        self.assertEqual(result['results'][0]['state'], 'awaiting_review')
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
