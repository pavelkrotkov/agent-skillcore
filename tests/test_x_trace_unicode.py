import json
import unittest

from x_trace_fixtures import SESSION, rollout, trace_fixture
from x_publication_fixtures import events
from x_curator.model_events import result
from x_curator.model_trace import envelope, pack, records, verify_request
from x_curator.worker_prompts import prompt


class UnicodeTraceTests(unittest.TestCase):
    def test_unicode_separators_survive_the_full_proof_round_trip(self):
        separators = 'before\u0085middle\u2028after\u2029end'
        request, _, rows = trace_fixture()
        request['bundle']['captures']['c']['text'] = separators
        rows[1]['payload']['content'][0]['text'] = prompt(request)
        packet = {'synthetic': separators}
        rows[-1]['payload']['content'][0]['text'] = json.dumps(packet, ensure_ascii=False)
        rows.insert(2, {'type': 'response_item', 'payload': {'type': 'function_call_output', 'output': separators}})
        proof = pack(request, prompt(request), ['synthetic'], events(packet, SESSION), rollout(rows))
        verify_request(proof, request)
        self.assertEqual(result(proof), (SESSION, packet))
        self.assertEqual(records(envelope(proof)['rollout'].encode()), rows)
        with self.assertRaises(ValueError):
            records(b'{"unterminated":"value\n')
