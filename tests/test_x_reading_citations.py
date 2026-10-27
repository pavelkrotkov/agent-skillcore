from copy import deepcopy

from x_reading_fixtures import ReadingCase
from x_curator import reading_citations, reading_packets, reading_plan, reading_views
from x_curator.evidence import bundle
from x_curator.publication_audit import audit


class ReadingCitationTests(ReadingCase):
    def book_request(self):
        evidence = bundle(self.db, self.token)
        plan = reading_plan.plan(evidence)
        index = next(i for i, spans in enumerate(plan['parts']) if any(p['capture'] == self.book for p in spans))
        return reading_views.request(evidence, plan, index, 'research')

    def test_line_selection_materializes_original_unicode_without_changing_author_output(self):
        request = self.book_request()
        raw = self.segment(request)
        original = deepcopy(raw)
        citation = reading_citations.citation(dict(capture=self.book, line_start='L000000', line_end='L000001'), request['bundle'])
        lines = request['bundle']['captures'][self.book]['text_lines']
        self.assertEqual(citation['quote'], lines['L000000'] + lines['L000001'])
        canonical = reading_citations.materialize(raw, request['bundle'])
        reading_packets.validate(canonical, request['bundle'])
        self.assertEqual(raw, original)
        self.assertEqual(canonical['claims'][0]['text'], raw['claims'][0]['text'])

    def test_missing_reversed_and_ambiguous_line_references_fail_closed(self):
        request = self.book_request()
        citation = dict(capture=self.book, line_start='L000000', line_end='L000001')
        changes = ({'line_end': 'L999999'}, {'line_start': 'L000002'}, {'quote': ''}, {'quote': 'invented'})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                reading_citations.citation(dict(citation, **change), request['bundle'])
        with self.assertRaises(ValueError):
            reading_citations.citation(dict(capture=self.book, quote='copied text'), request['bundle'])

    def test_authenticated_changed_selector_cannot_reuse_prior_canonical_approval(self):
        request = self.book_request()
        identity = self.publish_reading()
        role = f"read:{request['reading']['plan_sha']}:{request['reading']['index']}:research"
        row, request, raw = self.receipt(role)
        claim = next(c for c in raw['claims'] if c['citations'][0]['capture'] == self.book)
        claim['citations'][0]['line_end'] = 'L000001'
        self.replace_receipt(row['id'], request, raw)
        self.assertEqual(audit(self.db, self.root), [identity])
