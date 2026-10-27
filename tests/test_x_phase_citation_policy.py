import copy
import unittest

from x_curator import quick_compact, quick_prompt
from x_curator.native_search import MODE


def claim(capture):
    return dict(text='The original project names Morgan as manager.', kind='fact', attribution='Project filing',
                limitations=[], status='supported', sources=[dict(capture=capture, quote='Morgan is manager.',
                primary=True, credible=True, origin='Original project', reason='Direct primary statement.')])


class PhaseCitationPolicyTests(unittest.TestCase):
    def test_dispatched_phase_prompts_explain_the_enforced_evidence_boundary(self):
        requests = [dict(phase=dict(name=name)) for name in ('evidence', 'final')]
        requests.extend([dict(policy='quick-factcheck/v1', search_mode=MODE), dict(linked=True), {}])
        for request in requests:
            with self.subTest(request=request):
                prompt = quick_prompt.instructions(request)
                self.assertIn("kind:'text' with quick_excerpt:true", prompt)
                self.assertIn('x_detail', prompt)
                self.assertIn('attribution', prompt)
                self.assertIn('Judge the assertion actually made', prompt)
                self.assertIn('about the SAME subject', prompt)
                self.assertIn('unrelated true details cannot rescue', prompt)
                self.assertIn('Select central premises only after this correction test', prompt)
                self.assertNotIn("checks representing the item's main premise", prompt)
                self.assertNotIn('Choose the outcome in this order: a disproven central factual premise', prompt)
        final = quick_prompt.instructions(requests[1])
        self.assertIn("exactly ONE central factual claim with status:'disproven'", final)

    def test_invalid_context_citation_and_outcome_can_use_a_valid_body_backed_subset(self):
        evidence = dict(source='synthetic', captures={
            'context': dict(kind='x_detail', text='Morgan is manager.'),
            'body': dict(kind='text', quick_excerpt=True, text='Morgan is manager.')})
        decision = dict(format='compact-v1', outcome='disproven', reason='Synthetic draft.',
                        claims=[claim('context'), claim('body')])
        with self.assertRaisesRegex(ValueError, 'citation context: factual support needs an observed source body'):
            quick_compact.validate(decision, evidence)
        corrected = copy.deepcopy(decision)
        corrected['claims'] = corrected['claims'][1:]
        with self.assertRaisesRegex(ValueError, 'one central factual contradiction'):
            quick_compact.validate(corrected, evidence)
        corrected['outcome'] = 'supported'
        packet = quick_compact.validate(corrected, evidence)
        self.assertEqual(packet['claims'][0]['citations'][0]['capture'], 'body')
        self.assertEqual(decision['claims'][0]['sources'][0]['capture'], 'context')
