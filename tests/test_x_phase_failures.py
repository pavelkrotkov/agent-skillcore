from x_quick_phase_fixtures import PhaseCase
from x_curator.deadlines import DeadlineExceeded
from x_curator.worker_errors import WorkerFailure


class PhaseFailureTests(PhaseCase):
    def test_phase_cutoff_does_not_reset_a_finalization_deadline(self):
        def timeout(request):
            self.assertEqual(request['deadline'], self.started + 120)
            self.at = self.started + 120
            raise DeadlineExceeded('final turn did not complete in original allowance')
        self.assertIsNone(self.run_phases(timeout))
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM attempts').fetchone()[0], 1)
        self.assertIsNone(self.db.execute("SELECT finished FROM executions WHERE role='factcheck'").fetchone()[0])

    def test_provider_failure_is_not_a_normal_phase_cutoff_or_silent_retry(self):
        def failure(_request):
            raise WorkerFailure('synthetic provider interrupted', self.search_log)
        self.acquisition = failure
        self.assertIsNone(self.run_phases())
        self.assertEqual(self.final_calls, 0)
        self.assertIsNotNone(self.db.execute('SELECT * FROM provider_health').fetchone())

    def test_late_acquisition_stop_cannot_consume_the_reserved_final_window(self):
        def late(receipt):
            self.at = receipt['stopped'] = receipt['ended'] = self.started + 100
            return receipt
        self.cutoff_change = late
        self.assertIsNone(self.run_phases())
        self.assertEqual(self.final_calls, 0)
