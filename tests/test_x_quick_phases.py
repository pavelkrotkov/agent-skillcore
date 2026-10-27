from x_quick_phase_fixtures import PhaseCase
from x_curator import policy_metrics
from x_curator.publication_audit import audit


class QuickPhaseTests(PhaseCase):
    def test_interrupted_acquisition_then_genuine_final_shares_one_120_second_attempt(self):
        self.assertIsNotNone(self.run_phases())
        self.assertEqual(self.final_calls, 1)
        check = self.db.execute('SELECT * FROM quick_checks').fetchone()
        self.assertEqual((check['deadline'] - check['started'], check['searches']), (120, 4))
        phases = self.db.execute('SELECT role,started,finished FROM executions ORDER BY started').fetchall()
        self.assertEqual([(p['role'], p['finished'] - self.started) for p in phases],
                         [('factcheck_evidence', 80), ('factcheck', 110)])
        self.assertEqual(self.db.execute('SELECT count(*) FROM attempts').fetchone()[0], 1)
        self.assertEqual(self.calls, ['https://example.test/release'])
        self.assertEqual(audit(self.db, self.root), [])
        measured = policy_metrics.report(self.db)['runs'][0]
        self.assertEqual((measured['model_calls'], measured['observed_retries'], measured['search_limit']), (2, 0, None))
        self.assertEqual(measured['overruns'], [])
