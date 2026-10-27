import time
from unittest.mock import patch

from x_video_fixtures import PreparedVideoCase
from x_curator import prepared_video, quick_process, quick_store


class VideoBudgetTests(PreparedVideoCase):
    def test_verified_preparation_selects_180_but_old_120_deadline_is_immutable(self):
        started = time.time()
        original = quick_store.start(self.db, self.token, started)
        self.assertEqual(original['deadline'] - started, 120)
        prepared_video.store(self.db, self.job, self.payload(), 'Synthetic approval')
        resumed = quick_store.start(self.db, self.token, started + 20)
        self.assertEqual((resumed['id'], resumed['started'], resumed['deadline']),
                         (original['id'], started, original['deadline']))
        self.assertEqual(prepared_video.seconds(self.db, self.job), 180)

    def test_registry_tampering_cannot_extend_the_budget(self):
        identity = prepared_video.store(self.db, self.job, self.payload(), 'Synthetic approval')
        self.db.execute('UPDATE prepared_videos SET sha=? WHERE id=?', ('forged', identity))
        with self.assertRaisesRegex(ValueError, 'tampered prepared video'):
            quick_store.start(self.db, self.token, time.time())
        self.assertEqual(self.db.execute('SELECT count(*) FROM quick_checks').fetchone()[0], 0)

    def test_180_seconds_includes_setup_and_cannot_be_renewed(self):
        prepared_video.store(self.db, self.job, self.payload(), 'Synthetic approval')
        started = time.time()
        clock = [started]
        def run(db, state, client, token, check):
            self.assertEqual(check['deadline'], started + 180)
            clock[0] = started + 179
            self.assertEqual(quick_store.active(db, token)['id'], check['id'])
            clock[0] = started + 180
            return quick_store.active(db, token)
        with patch('time.time', side_effect=lambda: clock[0]), \
                patch('x_curator.quick_process.run', side_effect=run), \
                patch('x_curator.quick_process.until', wraps=quick_process.until) as limits:
            self.assertIsNone(quick_process.research(self.db, self.root, None, self.token))
        self.assertEqual([call.args[0] for call in limits.call_args_list], [started + 120, started + 180])
        check = self.db.execute('SELECT * FROM quick_checks').fetchone()
        self.assertEqual((check['deadline'], check['outcome']), (started + 180, 'inconclusive'))
        self.assertIn('allowance exhausted', check['reason'])
