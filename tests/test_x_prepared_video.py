import json
from unittest.mock import patch
from x_video_fixtures import PreparedVideoCase
from x_curator import blobs, prepared_video
from x_curator.evidence import bundle
from x_curator.receipts import encoded
from x_curator.prepared_video_proof import validate


class PreparedVideoTests(PreparedVideoCase):

    def test_cached_video_attaches_without_reacquisition_and_rejects_changed_transcript(self):
        payload = self.payload()
        identity = prepared_video.store(self.db, self.job, payload, 'Explicit synthetic approval')
        self.assertEqual(prepared_video.store(self.db, self.job, payload, 'Reuse'), identity)
        with patch('x_curator.public_http.exchange', side_effect=AssertionError('No network during check')):
            prepared_video.attach(self.db, self.token)
            captures = bundle(self.db, self.token)['captures']
        self.assertEqual(len([c for c in captures.values() if c.get('prepared_video')]), 1)
        with self.assertRaisesRegex(ValueError, 'coverage or text'):
            validate(self.db, dict(payload, text='Invented speech'))

    def test_foreign_preparation_and_corrupt_audio_fail_closed(self):
        payload = self.payload()
        identity = prepared_video.store(self.db, self.job, payload, 'Explicit synthetic approval')
        prepared_video.attach(self.db, self.token)
        self.db.execute('UPDATE prepared_videos SET source=? WHERE id=?', ('other', identity))
        with self.assertRaisesRegex(ValueError, 'foreign'):
            bundle(self.db, self.token)
        manifest = json.loads(blobs.read(self.db, payload['preparation_sha']))
        (self.root/'blobs'/manifest['parts'][0]['audio_sha']).write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'tampered acquisition'):
            validate(self.db, payload)

    def test_self_attested_profile_and_nonfinite_duration_are_rejected(self):
        payload = self.payload()
        config = self.root/'speech-config.json'
        config.write_text(json.dumps(dict(engine_sha='other', model_sha='other')))
        with self.assertRaisesRegex(ValueError, 'qualified profile'):
            validate(self.db, payload)
        config.write_text(json.dumps(dict(engine_sha='engine', model_sha='model')))
        manifest = json.loads(blobs.read(self.db, payload['preparation_sha']))
        manifest['duration'] = float('nan')
        payload['preparation_sha'] = blobs.put(self.db, encoded(manifest))
        with self.assertRaisesRegex(ValueError, 'duration is invalid'):
            validate(self.db, payload)

    def test_prepared_frames_reserve_space_inside_existing_photo_budget(self):
        from x_curator.quick_photo_scope import bounded_urls
        photos = [dict(rest_id='context', legacy=dict(extended_entities=dict(media=[
            dict(type='photo', media_url_https='https://example.test/'+str(i)) for i in range(40)])))]
        selected, omitted = bounded_urls(photos, '1', limit=8)
        self.assertEqual((len(selected), omitted), (8, 32))
