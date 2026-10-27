import json
from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_curator import blobs, http_receipts, youtube
from x_curator.http_ranges import WIDTH
from x_curator.receipts import encoded


URL = 'https://www.youtube.com/watch?v=Synthetic_1'


class YoutubeCase(PublicationCase):
    def setUp(self):
        super().setUp()
        self.job = self.db.execute('SELECT * FROM jobs').fetchone()
        self.data = {'134': b'v' * (WIDTH + 7), '140': b'a' * 17}
        self.formats = [dict(format_id=key, url='https://synthetic.googlevideo.com/' + key, filesize=len(body)) for key, body in self.data.items()]
        self.result = dict(id='Synthetic_1', live_status='not_live', duration=10, formats=self.formats)
        self.player = dict(videoDetails=dict(videoId='Synthetic_1', lengthSeconds='10', isLiveContent=False),
                           playabilityStatus=dict(status='OK'), streamingData=dict(adaptiveFormats=[
                               dict(itag=int(f['format_id']), url=f['url'], contentLength=str(f['filesize'])) for f in self.formats]))

    def exchange(self, url, method='GET', body=None, headers=None, max_bytes=None):
        if '/player' in url:
            return 200, [('Content-Type', 'application/json')], encoded(self.player)
        data = self.data[url.rsplit('/', 1)[-1]]
        start, end = map(int, headers['Range'][6:].split('-'))
        return 206, [('Content-Range', f'bytes {start}-{end}/{len(data)}'),
                     ('Content-Length', str(end-start+1)), ('ETag', '"synthetic-v1"')], data[start:end+1]

    def resolve(self, db, token, url):
        identity, _ = http_receipts.request(db, token, 'https://www.youtube.com/youtubei/v1/player', 'POST', b'{"videoId":"Synthetic_1"}')
        return self.result, [identity]

    # These fixtures isolate HTTP provenance; test_x_video exercises real local ffmpeg output.
    def merge(self, db, streams, duration):
        args = [piece for stream in streams for piece in ('-i', 'blobs/' + stream['body_sha'])]
        probe = dict(streams=[dict(codec_type='video'), dict(codec_type='audio')], format=dict(duration=duration))
        return dict(body_sha=blobs.put(db, b'synthetic merged body'), probe_sha=blobs.put(db, encoded(probe)),
                    version_sha=blobs.put(db, b'synthetic tool version'), args=args)

    def acquire_video(self):
        with patch('x_curator.public_http.exchange', side_effect=self.exchange), \
                patch('x_curator.youtube_resolver.resolve', side_effect=self.resolve), \
                patch('x_curator.youtube_merge.merge', side_effect=self.merge), \
                patch('x_curator.youtube.extract_video', side_effect=lambda _, p: dict(p, kind='video', text='Synthetic speech.')):
            payload = youtube.acquire(self.db, self.token, URL)
        self.manifest = json.loads(blobs.read(self.db, payload['youtube_sha']))
        return payload
