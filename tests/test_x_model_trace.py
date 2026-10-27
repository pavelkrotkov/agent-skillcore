from copy import deepcopy
from unittest.mock import patch
import unittest

from x_trace_fixtures import SESSION, rollout, trace_fixture
from x_curator.model_events import result
from x_curator.model_trace import pack, verify_request
from x_curator.worker_prompts import prompt


class TraceTests(unittest.TestCase):
    def test_full_native_receipts_bind_exact_request_and_survive_readback(self):
        request, log, rows = trace_fixture()
        proof = pack(request, prompt(request), ['synthetic'], log, rollout(rows))
        self.assertEqual(result(proof), (SESSION, {'synthetic': True}))
        with patch("x_curator.worker_prompts.prompt", return_value="Future instruction wording"):
            verify_request(proof, request)
        with self.assertRaises(ValueError):
            pack(request, 'missing evidence marker', [], log, rollout(rows))
        changed = deepcopy(request)
        changed['bundle']['captures']['c']['text'] += ' Altered evidence.'
        with self.assertRaisesRegex(ValueError, 'controller request'):
            verify_request(proof, changed)
        self.assertEqual(result(log), result(proof))

    def test_prompt_session_image_and_answer_changes_are_rejected(self):
        request, log, rows = trace_fixture()
        rows.insert(2, deepcopy(rows[-1]))
        variants = [deepcopy(rows) for _ in range(4)]
        variants[0][0]['payload']['id'] = 'different-session'
        variants[1][1]['payload']['content'][0]['text'] += ' trimmed'
        variants[2][1]['payload']['content'].pop()
        variants[3][-1]['payload']['content'][0]['text'] = '{}'
        for altered in variants:
            with self.subTest(altered=altered[0]['type']), self.assertRaises(ValueError):
                pack(request, prompt(request), ['synthetic'], log, rollout(altered))

    def test_compaction_and_truncation_block_even_completed_valid_json(self):
        request, log, rows = trace_fixture()
        rows.insert(2, deepcopy(rows[-1]))
        for marker in ('compacted', 'context_truncated'):
            with self.subTest(marker=marker), self.assertRaisesRegex(ValueError, 'compacted or truncated'):
                pack(request, prompt(request), [], log, rollout(rows + [{'type': marker, 'payload': {}}]))
