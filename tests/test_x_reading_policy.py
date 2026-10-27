from copy import deepcopy
from unittest.mock import patch

from x_reading_fixtures import ReadingCase
from x_curator import reading_plan
from x_curator.evidence import bundle
from x_curator.publication_audit import audit


class ReadingPolicyTests(ReadingCase):
    def test_wider_policy_covers_large_text_without_changing_page_policy(self):
        evidence = deepcopy(bundle(self.db, self.token))
        evidence['captures'][self.book]['text'] *= 2200
        with patch.dict(reading_plan.POLICIES, {1: {'width': 100000, 'context': 2000, 'max_segments': 16}}), self.assertRaisesRegex(ValueError, 'segment limit'):
            reading_plan.plan(evidence, 1)
        with patch('x_curator.reading_plan.CURRENT_VERSION', 3):
            plan = reading_plan.plan(evidence)
            self.assertEqual(plan['version'], 3)
            self.assertLessEqual(len(plan['parts']), 16)
            for key, capture in evidence['captures'].items():
                spans = [p for group in plan['parts'] for p in group if p['capture'] == key]
                self.assertEqual(''.join(capture['text'][p['start']:p['end']] for p in spans), capture['text'])
            evidence['captures'][self.book]['text'] = 'Synthetic page text.'
            with patch('x_curator.reading_plan.page_required', return_value=True):
                self.assertEqual(reading_plan.plan(evidence)['version'], 2)

    def test_new_policy_publication_keeps_full_chain_and_historical_replay(self):
        with patch('x_curator.reading_plan.CURRENT_VERSION', 3), patch.dict(
                'x_curator.reading_plan.POLICIES', {3: {'width': 800, 'context': 20, 'max_segments': 8}}):
            self.publish_reading()
            _, request, _ = self.receipt('research')
            self.assertEqual(request['reading']['plan']['version'], 3)
            self.assertGreater(len(request['reading']['receipts']), 1)
            with patch('x_curator.reading_plan.CURRENT_VERSION', 1):
                self.assertEqual(audit(self.db, self.root), [])
