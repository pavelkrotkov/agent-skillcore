from x_trace_fixtures import IMAGE, proof, trace_fixture
import json
import unittest

from x_curator.model_events import result
from x_curator.receipts import encoded
from x_curator.storage import sha256


class MalformedImageDiagnosticsTests(unittest.TestCase):
    def test_malformed_expected_hash_cannot_collide_with_a_missing_image_sentinel(self):
        request, _, _ = trace_fixture()
        log = json.loads(proof(request, {}, images={sha256(IMAGE): IMAGE}))
        rows = [json.loads(line) for line in log['rollout'].splitlines()]
        rows[1]['payload']['content'].pop()
        log['rollout'] = '\n'.join(encoded(row).decode() for row in rows)
        for invalid in ('missing', 'private-content-must-not-be-logged'):
            log['images'] = [invalid]
            with self.assertRaisesRegex(ValueError, 'actual=missing; expected=invalid') as caught:
                result(encoded(log))
            self.assertNotIn('private-content', str(caught.exception))
