import json
import unittest

from x_curator.receipts import digest
from x_curator.worker_prompts import prompt


class PromptBudgetTests(unittest.TestCase):
    def test_large_evidence_and_review_proposal_round_trip_without_loss(self):
        evidence = {'source': 'synthetic', 'captures': {'capture': {'text': ' α  quoted\n' * 45000}}}
        proposal = {'claims': [{'text': ' α  quoted\n', 'citations': ['capture']}]}
        for role in ('research', 'review'):
            request = {'role': role, 'bundle': evidence, 'bundle_sha': digest(evidence), 'proposal': proposal}
            rendered = prompt(request)
            payload = json.loads(rendered.split('\nUNTRUSTED EVIDENCE AND PROPOSAL:\n', 1)[1])
            self.assertGreater(len(rendered), 400000)
            self.assertEqual(payload, dict(request, proposal_sha=digest(proposal)))

    def test_complete_prompt_including_instructions_has_a_hard_bound(self):
        request = {'role': 'research', 'bundle': '', 'proposal': None}
        available = 1000000 - len(prompt(request))
        request['bundle'] = 'x' * available
        self.assertEqual(len(prompt(request)), 1000000)
        request['bundle'] += 'x'
        with self.assertRaisesRegex(ValueError, 'segmented reading'):
            prompt(request)
