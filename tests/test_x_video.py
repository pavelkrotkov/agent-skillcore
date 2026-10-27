import shutil
import subprocess
import unittest

from x_publication_fixtures import PublicationCase
from x_curator.blobs import put, read
from x_curator.video_frames import sample_frames
from x_curator.youtube_merge import merge, verify_merge


@unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg is an operational dependency')
class VideoTests(PublicationCase):
    def test_local_stream_merge_is_reproducible_and_readback_checks_output(self):
        video, audio = self.root / 'video.mp4', self.root / 'audio.m4a'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=64x64:r=5:d=1',
                        '-c:v', 'mpeg4', str(video)], capture_output=True, check=True, timeout=20)
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
                        '-c:a', 'aac', str(audio)], capture_output=True, check=True, timeout=20)
        streams = [dict(body_sha=put(self.db, path.read_bytes())) for path in (video, audio)]
        first, second = merge(self.db, streams, 1), merge(self.db, streams, 1)
        self.assertEqual(first['body_sha'], second['body_sha'])
        verify_merge(self.db, first, first, 1, streams)
        with self.assertRaisesRegex(ValueError, 'controller merge'):
            verify_merge(self.db, first, dict(body_sha=streams[0]['body_sha']), 1, streams)

    def test_sampling_avoids_container_tail_after_last_video_frame(self):
        video = self.root / 'synthetic.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=64x64:r=5:d=1',
                        '-c:v', 'mpeg4', str(video)], capture_output=True, check=True, timeout=20)
        sha = put(self.db, video.read_bytes())
        frames = sample_frames(self.db, self.root / 'blobs' / sha, 1.024)
        self.assertEqual(len(frames), 6)
        for frame in frames:
            self.assertTrue(read(self.db, frame['sha']).startswith(b'\x89PNG'))
