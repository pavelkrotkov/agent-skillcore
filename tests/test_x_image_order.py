import json
import unittest

from x_trace_fixtures import proof
from x_curator.model_events import result
from x_curator.model_trace import verify_request
from x_curator.receipts import encoded
from x_curator.storage import sha256


class ImageOrderTests(unittest.TestCase):
    def test_new_receipts_bind_order_and_legacy_receipts_cannot_upgrade_pdf_pages(self):
        images = {sha256(body): body for body in (b'synthetic image A', b'synthetic image B')}
        request = {'role': 'research', 'bundle': {'captures': {'c': {'kind': 'image', 'images': list(images)}}}, 'proposal': None}
        receipt = json.loads(proof(request, {}, images=images))
        rows = [json.loads(line) for line in receipt['rollout'].splitlines()]
        content = rows[1]['payload']['content']
        content[1:] = reversed(content[1:])
        receipt['rollout'] = '\n'.join(encoded(row).decode() for row in rows)
        with self.assertRaisesRegex(ValueError, 'image bytes differ'):
            result(encoded(receipt))
        receipt['format'] = 'x-curator-input-proof-v1'
        verify_request(encoded(receipt), request)
        request['bundle']['captures']['c']['kind'] = 'pdf'
        receipt = json.loads(proof(request, {}, images=images))
        receipt['format'] = 'x-curator-input-proof-v1'
        with self.assertRaisesRegex(ValueError, 'ordered image proofs'):
            verify_request(encoded(receipt), request)
