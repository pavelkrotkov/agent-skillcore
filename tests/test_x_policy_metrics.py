from unittest.mock import patch

from x_batch_fixtures import BatchCase
from x_curator import policy_metrics


class PolicyMetricsTests(BatchCase):
    def test_report_measures_actual_admission_and_flags_late_model_receipts(self):
        self.run_batch()
        report = policy_metrics.report(self.db)
        self.assertEqual(report['cohort_counts'], {'supported': 1})
        run = report['runs'][0]
        self.assertEqual((run['model_calls'], run['searches'], run['observed_retries']), (1, 1, 0))
        self.assertGreater(run['processing_seconds'], 0)
        self.assertGreaterEqual(run['capture_to_disposition_seconds'], run['processing_seconds'])
        self.assertEqual(run['overruns'], [])
        self.assertGreater(report['source_publication_latency_seconds'], 0)
        with self.db:
            self.db.execute('UPDATE executions SET finished=(SELECT deadline+1 FROM quick_checks)')
        self.assertEqual(policy_metrics.report(self.db)['qualification'], 'failed')

    def test_failed_unfinished_execution_is_visible_and_never_claimed_as_qualified(self):
        self.checker = lambda request: b'not a model receipt'
        self.run_batch()
        report = policy_metrics.report(self.db)
        self.assertEqual(report['cohort_counts'], {'failed_processing': 1})
        self.assertEqual(report['runs'][0]['unfinished_receipts'], 1)
        self.assertEqual(report['runs'][0]['model_calls'], 1)
        self.assertEqual(report['qualification'], 'inspect_live_evidence')
        self.assertIsNone(report['source_publication_latency_seconds'])

    def test_interrupted_publication_latency_includes_actual_recovery_delay(self):
        from x_curator.publication_files import write_verified
        from x_curator.publication_recovery import complete
        def interrupted(*args):
            write_verified(*args)
            raise OSError('synthetic interruption after write')
        with patch('x_curator.publication.write_verified', side_effect=interrupted):
            self.run_batch()
        page = self.db.execute('SELECT id,created FROM publications').fetchone()
        self.assertIsNone(policy_metrics.first_publication(self.db))
        with patch('x_curator.publication_recovery.time.time', return_value=page['created'] + 30):
            complete(self.db, self.root, page['id'], 'Verified recovery for timing regression')
        self.assertGreaterEqual(policy_metrics.first_publication(self.db), 30)
        with self.db:
            self.db.execute('DELETE FROM publication_recoveries')
        self.assertIsNone(policy_metrics.first_publication(self.db))
