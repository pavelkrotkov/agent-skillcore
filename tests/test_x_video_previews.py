from copy import deepcopy
import shutil
import unittest
from x_video_preview_fixtures import VideoPreviewCase, frame
from x_curator import blobs, media_presentations, video_preview_pixels
from x_curator.media_inputs import attachments


@unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg is an operational dependency')
class VideoPreviewTests(VideoPreviewCase):
    def test_real_attachment_path_keeps_all_frame_bindings_and_reduces_pixels(self):
        before = deepcopy(self.evidence)
        records = media_presentations.prepare(self.db, self.evidence)
        paths = attachments(self.db, self.root / 'previews', self.evidence, records)
        self.assertEqual(self.evidence, before)
        self.assertEqual([r['original'] for r in records], sorted(self.video['images']))
        self.assertEqual([p.stem for p in paths], [r['presented'] for r in records])
        self.assertEqual(len(paths), 24)
        self.assertEqual({media_presentations.dimensions(p.read_bytes()) for p in paths}, {(432, 768)})
        original_bytes = sum(len(blobs.read(self.db, sha)) for sha in self.video['images'])
        self.assertLess(sum(p.stat().st_size for p in paths), original_bytes)

    def test_unrelated_pixels_and_changed_original_binding_are_rejected(self):
        records = media_presentations.prepare(self.db, self.evidence)
        video_preview_pixels.VERIFIED.clear()
        media_presentations.verify(self.db, self.evidence, records[:1])
        forged = deepcopy(records[:1])
        forged[0]['presented'] = blobs.put(self.db, frame(250, 432, 768))
        with self.assertRaisesRegex(ValueError, 'pixels do not derive'):
            attachments(self.db, self.root / 'forged', self.evidence, forged)
        records[0]['original'] = blobs.put(self.db, frame(250))
        with self.assertRaisesRegex(ValueError, 'foreign or repeated original'):
            attachments(self.db, self.root / 'foreign', self.evidence, records)

    def test_small_frames_and_photos_keep_original_bytes(self):
        small = blobs.put(self.db, frame(250, 64, 64))
        self.video['images'] = [small]
        photo = blobs.put(self.db, frame(251))
        self.evidence['captures']['photo'] = dict(kind='image', images=[photo])
        self.assertEqual(media_presentations.prepare(self.db, self.evidence), [])
        paths = attachments(self.db, self.root / 'originals', self.evidence)
        self.assertEqual({p.stem for p in paths}, {small, photo})
