import copy
from unittest.mock import patch

from x_youtube_fixtures import YoutubeCase, URL
from x_curator import blobs, http_receipts, youtube_audit, youtube_media
from x_curator.evidence import current_bundle, save_capture
from x_curator.youtube_player import verify_player
from x_curator.youtube_stream_audit import verify_stream


class YoutubeTests(YoutubeCase):
    def test_complete_capture_replays_without_active_lease_or_network(self):
        payload = self.acquire_video()
        save_capture(self.db, self.token, payload)
        with self.db:
            self.db.execute("UPDATE jobs SET lease_until=0")
        with patch('x_curator.public_http.exchange', side_effect=AssertionError('audit must stay offline')):
            current_bundle(self.db, self.job, self.token)
        self.assertEqual(self.db.execute('SELECT count(*) FROM retrievals').fetchone()[0], 4)
        (self.root / 'blobs' / payload['body_sha']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'tampered'):
            current_bundle(self.db, self.job, self.token)

    def test_range_assembly_rejects_gaps_order_duplicates_and_wrong_source(self):
        self.acquire_video()
        stream = self.manifest['streams'][0]
        for receipts in (stream['receipts'][:1], list(reversed(stream['receipts'])), stream['receipts'] * 2):
            with self.subTest(receipts=receipts), self.assertRaises(ValueError):
                verify_stream(self.db, dict(stream, receipts=receipts), self.job)
        with self.assertRaisesRegex(ValueError, 'belong'):
            http_receipts.read(self.db, stream['receipts'][0], dict(account='other', id='1'))

    def test_identity_is_bound_to_player_receipt_and_original_capture(self):
        payload = self.acquire_video()
        with self.assertRaisesRegex(ValueError, 'identity differs'):
            youtube_audit.verify(self.db, dict(payload, url=URL.replace('Synthetic_1', 'Synthetic_2')), self.job)
        value = copy.deepcopy(self.formats[0])
        value['url'] += '?different'
        with self.assertRaisesRegex(ValueError, 'authentic player'):
            verify_player(value, self.player['streamingData']['adaptiveFormats'])

    def test_known_media_size_cannot_partially_consume_insufficient_budget(self):
        self.acquire_video()
        selected = [dict(self.formats[0], filesize=40 * 1048576)]
        with self.assertRaisesRegex(ValueError, 'remaining lifetime'):
            youtube_media.budget(self.db, self.token, selected)
        self.assertEqual(self.db.execute('SELECT count(*) FROM retrievals').fetchone()[0], 4)

    def test_private_receipt_tampering_fails_readback(self):
        payload = self.acquire_video()
        receipt = self.manifest['streams'][0]['receipts'][0]
        with self.db:
            self.db.execute('UPDATE retrievals SET body_sha=? WHERE id=?', (blobs.put(self.db, b'changed'), receipt))
        with self.assertRaisesRegex(ValueError, 'reserved request'):
            youtube_audit.verify(self.db, payload, self.job)
