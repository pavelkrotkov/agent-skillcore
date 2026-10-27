import json
from x_video_fixtures import PreparedVideoCase
from x_curator import blobs
from x_curator.receipts import encoded
from x_curator.prepared_video_proof import validate


class VideoAudioCoverageTests(PreparedVideoCase):
    def test_complete_audio_may_end_before_the_video_but_partial_audio_is_rejected(self):
        payload = self.payload()
        manifest = json.loads(blobs.read(self.db, payload['preparation_sha']))
        manifest['duration'] = 1.2
        payload['preparation_sha'] = blobs.put(self.db, encoded(manifest))
        validate(self.db, payload)
        manifest['transcribed_duration'] = .5
        payload['preparation_sha'] = blobs.put(self.db, encoded(manifest))
        with self.assertRaisesRegex(ValueError, 'coverage or text changed'):
            validate(self.db, payload)
