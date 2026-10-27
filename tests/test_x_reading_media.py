from unittest.mock import patch

from x_reading_fixtures import ReadingCase
from x_curator import blobs
from x_curator.evidence import save_capture
from x_curator.publication_audit import audit


class ReadingMediaTests(ReadingCase):
    def test_segment_media_is_attached_and_tampered_original_pixels_invalidate_publication(self):
        sha = blobs.put(self.db, b'\x89PNG\r\n\x1a\nsynthetic image')
        save_capture(self.db, self.token, dict(kind='image', url='https://example.test/image',
                                              text='Synthetic image context.', images=[sha], body_sha=sha))
        identity = self.publish_reading()
        shown = [r for r in self.calls if sha in {s for c in r['bundle']['captures'].values() for s in c.get('images', [])}]
        self.assertEqual({r['role'] for r in shown}, {'research', 'review'})
        (self.root / 'blobs' / sha).write_bytes(b'damaged pixels')
        self.assertEqual(audit(self.db, self.root), [identity])

    def test_independently_approved_zero_claim_interval_is_retained_in_complete_reading_chain(self):
        original = self.segment
        def empty(request):
            packet = original(request)
            if request['reading']['index'] == 0:
                packet.update(claims=[], empty_reason='This synthetic interval is only a separator.')
            return packet
        with patch.object(self, 'segment', side_effect=empty):
            self.publish_reading()
        _, request, _ = self.receipt('research')
        self.assertEqual(len(request['reading']['receipts']), len(request['reading']['plan']['parts']))
        self.assertEqual(audit(self.db, self.root), [])
