import json
import unittest

from x_trace_fixtures import trace_fixture, rollout
from x_curator.model_trace import pack, verify_input, verify_request
from x_curator.receipts import encoded
from x_curator.worker_prompts import prompt


class RolloutInputOnlyTests(unittest.TestCase):
    def test_authentic_interrupted_input_cannot_be_used_as_completed_execution(self):
        request, events, rows = trace_fixture()
        proof = json.loads(pack(request, prompt(request), [], events, rollout(rows)))
        proof['events'] = '\n'.join(events.decode().splitlines()[:-1]) + '\n'
        proof['rollout'] = rollout(rows[:-1]).decode()
        verify_input(proof, request)
        with self.assertRaisesRegex(ValueError, 'incomplete model execution'):
            verify_request(encoded(proof), request)
        proof['rollout'] = rollout(rows[:-1] + [dict(type='compacted', payload={})]).decode()
        with self.assertRaisesRegex(ValueError, 'compacted or truncated'):
            verify_input(proof, request)

    def test_partial_input_still_rejects_foreign_session_and_prompt(self):
        request, events, rows = trace_fixture()
        proof = json.loads(pack(request, prompt(request), [], events, rollout(rows)))
        rows[0]['payload']['id'] = 'foreign'
        proof['rollout'] = rollout(rows).decode()
        with self.assertRaisesRegex(ValueError, 'session'):
            verify_input(proof, request)
        proof['request_sha'] = 'tampered'
        with self.assertRaisesRegex(ValueError, 'controller request'):
            verify_input(proof, request)

    def test_deferred_evidence_pixels_remain_mandatory_in_final_phase(self):
        request, events, rows = trace_fixture()
        request.update(role='factcheck', policy='quick-factcheck/v1',
                       phase=dict(name='evidence', image_policy='deferred-to-final'))
        rows[1]['payload']['content'] = [dict(type='input_text', text=prompt(request))]
        proof = json.loads(pack(request, prompt(request), [], events, rollout(rows)))
        self.assertEqual(proof['images'], [])
        request['phase']['name'] = 'final'
        rows[1]['payload']['content'][0]['text'] = prompt(request)
        with self.assertRaisesRegex(ValueError, 'image bytes differ'):
            pack(request, prompt(request), [], events, rollout(rows))
