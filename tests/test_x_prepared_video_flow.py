from unittest.mock import patch
import os
from x_video_fixtures import PreparedVideoCase
from x_curator import blobs, prepared_video


class PreparedVideoFlowTests(PreparedVideoCase):
    def test_captions_keep_observed_words_and_reject_out_of_video_timestamps(self):
        from x_curator.video_captions import text
        body = b'WEBVTT\n\n00:00.000 --> 00:01.000\n<v speaker>Observed words</v>\n'
        self.assertIn('[0.0-1.0] Observed words', text(body, 1))
        with self.assertRaisesRegex(ValueError, 'out of bounds'):
            text(body, .5)

    def test_prepared_media_is_in_native_context_and_publishes_inside_original_allowance(self):
        from x_quick_fixtures import native
        from x_curator import quick_process
        from x_curator.publication_audit import audit
        payload = self.payload()
        prepared_video.store(self.db, self.job, payload, 'Explicit synthetic approval')
        def checker(request):
            from x_curator.worker_prompts import prompt
            self.assertIn('Controller-prepared video', prompt(request))
            capture = next(k for k, c in request['bundle']['captures'].items() if c.get('prepared_video'))
            source = dict(capture=capture, quote='A recorded recommendation', primary=True,
                          credible=True, origin='Recorded speaker', reason='Directly observed recommendation')
            decision = dict(format='compact-v1', outcome='supported', reason='Attributed recommendation',
                            claims=[dict(text='The speaker recommends a synthetic approach.', kind='recommendation',
                                         status='subjective', attribution='Synthetic speaker', limitations=[], sources=[source])])
            return native(request, decision, [], images={i:blobs.read(self.db, i) for i in payload['images']})
        with patch('x_curator.quick_process.runner', return_value=checker), \
             patch('x_curator.public_http.exchange', side_effect=AssertionError('No media acquisition in checker')), \
             patch.dict(os.environ):
            os.environ.pop('X_CURATOR_SPEECH_CONFIG', None)
            publication = quick_process.research(self.db, self.root, None, self.token)
        self.assertIsNotNone(publication)
        self.assertEqual(audit(self.db, self.root), [])
        check = self.db.execute('SELECT started,deadline FROM quick_checks').fetchone()
        self.assertEqual(check['deadline']-check['started'], 180)
