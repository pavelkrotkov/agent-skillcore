from unittest.mock import patch

from x_quick_phase_fixtures import PhaseCase
from x_curator.publication_audit import audit


class VideoPhaseBudgetTests(PhaseCase):
    def test_verified_video_finalizes_at_170_without_extending_acquisition(self):
        def final(request):
            self.assertEqual((request['deadline'], self.initial['phase']['cutoff']),
                             (self.started + 180, self.started + 80))
            proof = self.final(request)
            self.at = self.started + 170
            return proof
        with patch('x_curator.prepared_video.seconds', return_value=180):
            self.assertIsNotNone(self.run_phases(final))
        self.assertEqual(audit(self.db, self.root), [])
        self.assertEqual(self.db.execute('SELECT count(*) FROM attempts').fetchone()[0], 1)

    def test_video_final_after_180_cannot_publish_or_renew_check(self):
        def final(request):
            proof = self.final(request)
            self.at = self.started + 181
            return proof
        with patch('x_curator.prepared_video.seconds', return_value=180):
            self.assertIsNone(self.run_phases(final))
        check = self.db.execute('SELECT * FROM quick_checks').fetchone()
        self.assertEqual((check['deadline'], check['outcome']), (self.started + 180, 'inconclusive'))
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
