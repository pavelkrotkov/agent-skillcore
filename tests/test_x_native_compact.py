import json

from x_native_search_fixtures import NativeCase
from x_curator.publication_audit import audit
from x_curator import quick_mcp, quick_store


def compact(selection, value):
    check = value['checks'][0]
    fact = {'text': check['text'], 'kind': 'fact', 'attribution': 'Original project', 'limitations': [],
            'status': check['status'], 'sources': check['sources']}
    opinion = {'text': 'Synthetic evidence.', 'kind': 'opinion', 'attribution': 'Synthetic author',
               'limitations': [], 'status': 'subjective', 'sources': [{'capture': selection,
               'quote': 'Synthetic evidence.', 'primary': False, 'credible': False,
               'origin': 'Liked post author', 'reason': 'Direct selection supports attribution.'}]}
    return {'format': 'compact-v1', 'outcome': 'supported', 'reason': 'Primary source supports the year.',
            'claims': [fact, opinion]}


class NativeCompactTests(NativeCase):
    def test_invalid_kind_is_corrected_inside_the_same_execution_and_allowance(self):
        selection = next(key for key, value in self.evidence['captures'].items() if value['kind'] == 'selection')

        def correct(value):
            decision = compact(selection, value)
            decision['claims'][0]['kind'] = 'factual'
            before = dict(quick_store.active(self.db, self.token))
            rejected = quick_mcp.call(self.db, self.token, 'validate', {'decision': decision})
            self.assertTrue(rejected['isError'])
            self.assertIn('unknown epistemic assessment', rejected['content'][0]['text'])
            self.tools.append(rejected)
            decision['claims'][0]['kind'] = 'fact'
            self.assertEqual(dict(quick_store.active(self.db, self.token)), before)
            return decision

        self.modify = correct
        self.assertIsNotNone(self.run_check())
        self.assertEqual(audit(self.db, self.root), [])
        self.assertEqual(self.db.execute('SELECT count(*) FROM executions').fetchone()[0], 1)
        self.assertEqual(self.db.execute('SELECT count(*) FROM attempts').fetchone()[0], 1)

    def test_native_compact_verdict_publishes_with_attribution(self):
        selection = next(key for key, value in self.evidence['captures'].items() if value['kind'] == 'selection')
        self.modify = lambda value: compact(selection, value)
        identity = self.run_check()
        self.assertIsNotNone(identity)
        output = json.loads(self.db.execute('SELECT output FROM executions').fetchone()[0])
        self.assertEqual(output['format'], 'compact-v1')
        body = self.db.execute('SELECT body FROM publications').fetchone()[0].decode()
        self.assertIn('Attribution: Synthetic author', body)
        self.assertEqual(audit(self.db, self.root), [])

    def test_irrelevant_native_body_stays_specific_inconclusive(self):
        self.fetch = lambda _url: (200, 'text/plain', b'Unrelated material.', None)
        self.modify = lambda _value: {'format': 'compact-v1', 'outcome': 'inconclusive',
                                      'reason': 'Which authoritative source establishes the release year?', 'claims': []}
        self.assertIsNone(self.run_check())
        check = self.db.execute('SELECT outcome,reason FROM quick_checks').fetchone()
        self.assertEqual(tuple(check), ('inconclusive', 'Which authoritative source establishes the release year?'))
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
