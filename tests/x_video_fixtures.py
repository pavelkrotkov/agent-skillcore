import json
import os
from unittest.mock import patch

from x_fixtures import Client, CollectionCase, collect, envelope, tweet_entry
from test_x_speech import audio
from x_curator import blobs, prepared_video
from x_curator.evidence import capture_selection, bundle
from x_curator.leases import claim
from x_curator.queue import enqueue
from x_curator.receipts import digest, encoded
from x_curator.video_transcript import text


class PreparedVideoCase(CollectionCase):
    def setUp(self):
        super().setUp()
        self.url = 'https://video.example.test/clip.mp4'
        entry = tweet_entry('1')
        entry['content']['itemContent']['tweet_results']['result']['legacy'] = dict(
            full_text='A clip', extended_entities=dict(media=[dict(type='video', video_info=dict(
                variants=[dict(content_type='video/mp4', bitrate=100, url=self.url)]))]))
        collect(self.db, Client([(200, envelope([dict(type='TimelineAddEntries', entries=[entry])]))]), 'likes', delay=0)
        enqueue(self.db)
        self.job = claim(self.db, Client.account)
        self.token = self.job['token']
        capture_selection(self.db, self.token)
        config = self.root/'speech-config.json'
        config.write_text(json.dumps(dict(engine_sha='engine', model_sha='model')))
        env = patch.dict(os.environ, X_CURATOR_SPEECH_CONFIG=str(config))
        env.start()
        self.addCleanup(env.stop)

    def payload(self):
        wav = audio()
        profile = dict(engine_sha='engine', model_sha='model')
        receipt = dict(profile, audio_sha=blobs.put(self.db, wav), duration=1.0,
                       segments=[dict(start=0, end=1, text='A recorded recommendation')])
        image = blobs.put(self.db, b'\x89PNG\r\n\x1a\nsynthetic')
        frames = [dict(at=.5, sha=image)]
        raw = blobs.put(self.db, b'synthetic media')
        manifest = dict(media_sha=raw, url=self.url, duration=1, audio_duration=1, transcribed_duration=1, profile=profile, frames=frames,
                        revision=prepared_video.revision(self.db, self.job),
                        parts=[dict(offset=0, audio_sha=receipt['audio_sha'], receipt_sha=blobs.put(self.db, encoded(receipt)))])
        return dict(kind='video', url=self.url, body_sha=raw, images=[image], frames=frames,
                    text=text([dict(offset=0, receipt=receipt)]), preparation_sha=blobs.put(self.db, encoded(manifest)),
                    limitations=['Synthetic sampled frames and machine transcript'])
