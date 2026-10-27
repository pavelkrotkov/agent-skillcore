from copy import deepcopy

from x_reading_fixtures import ReadingCase
from x_curator import reading_citations, reading_packets, reading_plan, reading_views
from x_curator.evidence import bundle
from x_curator.receipts import digest


class ReadingPlanTests(ReadingCase):
    def test_unicode_intervals_cover_every_original_character_and_context_is_labeled(self):
        evidence = bundle(self.db, self.token)
        plan = reading_plan.plan(evidence)
        intervals = [p for group in plan['parts'] for p in group if p['capture'] == self.book]
        text = evidence['captures'][self.book]['text']
        self.assertEqual(''.join(text[p['start']:p['end']] for p in intervals), text)
        for index in range(len(plan['parts'])):
            view = reading_views.view(evidence, plan, index)
            self.check_fragments(evidence, view, plan['parts'][index])
        self.assertEqual(plan['bundle_sha'], digest(evidence))

    def check_fragments(self, evidence, view, parts):
        for part in parts:
            original = evidence['captures'][part['capture']]['text']
            primary = reading_citations.captures(view)[part['capture']]['text']
            self.assertEqual(primary, original[part['start']:part['end']])
            context = view['boundary_context'][part['capture']]
            self.assertTrue(original[:part['start']].endswith(context['before']))
            self.assertTrue(original[part['end']:].startswith(context['after']))
            self.assertLessEqual(max(map(len, context.values())), reading_plan.POLICIES[1]['context'])
            self.assertEqual(part['capture_sha'], digest(evidence['captures'][part['capture']]))
            if part['capture'] == self.book:
                self.assertTrue(original[:part['end']].endswith('\n'))

    def test_segment_cannot_cite_unseen_text_and_zero_claims_require_explanation(self):
        evidence = bundle(self.db, self.token)
        plan = reading_plan.plan(evidence)
        request = reading_views.request(evidence, plan, 0, 'research')
        packet = reading_citations.materialize(self.segment(request), request['bundle'])
        packet['claims'][0]['citations'][0]['quote'] = 'ABSENT FROM THE VISIBLE SLICE'
        with self.assertRaises(ValueError):
            reading_packets.validate(packet, request['bundle'])
        packet['claims'] = []
        with self.assertRaises(ValueError):
            reading_packets.validate(packet, request['bundle'])
        packet['empty_reason'] = 'Synthetic interval contains only bibliographic separators.'
        reading_packets.validate(packet, request['bundle'])

    def test_segment_limit_rejects_before_any_model_call(self):
        evidence = deepcopy(bundle(self.db, self.token))
        evidence['captures'][self.book]['text'] *= 20
        with self.assertRaisesRegex(ValueError, 'segment limit'):
            reading_plan.plan(evidence)
        self.assertEqual(self.calls, [])
