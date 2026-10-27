from unittest.mock import patch
from x_video_fixtures import PreparedVideoCase
from x_curator import prepared_video


class PreparedVideoScopeTests(PreparedVideoCase):
    def test_package_rejects_special_files_before_reading(self):
        import os
        from x_curator.video_package import body
        root = self.root.resolve()
        os.mkfifo(root / 'named-pipe')
        with self.assertRaisesRegex(ValueError, 'bounded directory'):
            body(root, 'named-pipe')

    def test_empty_short_audio_cannot_bypass_chunk_coverage(self):
        from x_curator.video_transcript import validate
        with self.assertRaisesRegex(ValueError, 'requires observed audio chunks'):
            validate(self.db, dict(duration=.01, parts=[]))

    def test_prepared_evidence_requires_a_live_owned_lease(self):
        prepared_video.store(self.db, self.job, self.payload(), 'Explicit synthetic approval')
        with self.assertRaisesRegex(ValueError, 'lease'):
            prepared_video.attach(self.db, 'unknown-token')

    def test_post_frame_capacity_is_checked_before_a_quick_attempt(self):
        from x_curator.prepared_video_urls import capacity
        prepared_video.store(self.db, self.job, self.payload(), 'Explicit synthetic approval')
        with self.assertRaisesRegex(ValueError, 'aggregate frame budget'):
            capacity(self.db, self.job, prepared_video.revision(self.db, self.job), dict(images=list(map(str, range(24)))))

    def test_registration_rechecks_revision_after_package_validation(self):
        payload = self.payload()
        with patch('x_curator.prepared_video_store.revision', return_value='changed'):
            with self.assertRaisesRegex(ValueError, 'revision changed during registration'):
                prepared_video.store(self.db, self.job, payload, 'Explicit synthetic approval')
