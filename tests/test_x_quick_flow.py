import json
from unittest.mock import patch

from x_quick_fixtures import QuickCase, native
from x_curator import quick_process, quick_store
from x_curator.publication_audit import audit
from x_curator.wiki_sources import sources
from x_curator.model_trace import envelope, records


class QuickFlowTests(QuickCase):
    def test_truncated_reader_transport_still_prevents_publication(self):
        checker = self.checker
        def truncated(request):
            log = checker(request)
            rows = records(envelope(log)['rollout'].encode())
            outputs = [json.loads(r['payload']['output']) for r in rows if r.get('payload', {}).get('type') == 'function_call_output']
            outputs[-1]['content'][0]['text'] = outputs[-1]['content'][0]['text'][:100]
            return native(request, self.decision, outputs)
        self.checker = truncated
        self.assertIsNone(self.run_check())
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
        self.assertIn('absent from original model rollout', self.db.execute('SELECT reason FROM quick_checks').fetchone()[0])

    def run_check(self):
        with patch('x_curator.quick_web.fetch', self.fetch), patch('x_curator.quick_search.fetch', self.fetch), patch('x_curator.quick_process.runner', return_value=self.checker):
            return quick_process.research(self.db, self.root, self.client, self.token)

    def test_supported_check_publishes_and_replays_into_existing_wiki(self):
        identity = self.run_check()
        self.assertIsNotNone(identity)
        self.assertEqual(audit(self.db, self.root), [])
        self.assertEqual(set(sources(self.db, self.root)), {identity})
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.db.execute('SELECT role FROM executions').fetchall()[0][0], 'factcheck')
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'published')

    def test_disproven_central_premise_is_excluded_with_reason(self):
        def disprove(value):
            value['checks'][0]['status'] = 'disproven'
            value.update(outcome='disproven', reason='Original evidence disproves the central claim.')
            value.pop('packet')
            return value
        self.modify = disprove
        self.assertIsNone(self.run_check())
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'excluded')
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)

    def test_unavailable_evidence_is_pending_never_false(self):
        def unavailable(_):
            raise OSError('synthetic unavailable search')
        self.fetch = unavailable
        self.assertIsNone(self.run_check())
        self.assertEqual(self.db.execute('SELECT outcome FROM quick_checks').fetchone()[0], 'inconclusive')
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'awaiting_review')

    def test_authenticated_model_cannot_publish_unsupported_attributed_facts(self):
        def unsupported(value):
            value['checks'][0]['status'] = 'inconclusive'
            value['packet']['claims'][0]['kind'] = 'recommendation'
            return value
        self.modify = unsupported
        self.assertIsNone(self.run_check())
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)

    def test_substituted_dynamic_evidence_invalidates_publication(self):
        identity = self.run_check()
        with self.db:
            self.db.execute("UPDATE quick_tools SET output=replace(output,'released in 2025','released in 2024') WHERE name='read'")
        self.assertEqual(audit(self.db, self.root), [identity])

    def test_corrupt_empty_tool_content_invalidates_without_crashing_audit(self):
        identity = self.run_check()
        with self.db:
            self.db.execute('UPDATE quick_tools SET output=?', ('{"content":[],"isError":false}',))
        self.assertEqual(audit(self.db, self.root), [identity])
