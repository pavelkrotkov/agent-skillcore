import sys
import time
from unittest.mock import patch

from x_native_search_fixtures import NativeCase
from x_curator import native_search_trace, process_group, provider_health, quick_process
from x_curator.worker_errors import WorkerFailure


class NativeDeadlineTests(NativeCase):
    def timeout_checker(self, request):
        output = self.root / 'timeout.jsonl'
        script = 'import sys,time; sys.stdout.buffer.write(%r); sys.stdout.flush(); time.sleep(30)' % self.search_log
        with output.open('wb') as stream:
            return process_group.execute([sys.executable, '-c', script], b'',
                                         dict(request, deadline=time.time() + 0.3), output=output, stdout=stream)

    def test_killed_execution_retains_usage_without_publication_or_provider_cooldown(self):
        started = time.monotonic()
        with patch('x_curator.quick_process.runner', return_value=self.timeout_checker):
            self.assertIsNone(quick_process.research(self.db, self.root, self.client, self.token))
        self.assertLess(time.monotonic() - started, 2)
        execution = self.db.execute('SELECT * FROM executions').fetchone()
        self.assertEqual(execution['log'], self.search_log)
        self.assertIsNone(execution['finished'])
        check = self.db.execute('SELECT * FROM quick_checks').fetchone()
        self.assertEqual((check['searches'], check['outcome']), (4, 'inconclusive'))
        self.assertIn('DeadlineExceeded', check['reason'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
        self.assertIsNone(provider_health.blocked(self.db))

    def test_provider_failure_also_retains_completed_search_usage(self):
        def failed(_request):
            raise WorkerFailure('synthetic provider interruption', self.search_log)
        with patch('x_curator.quick_process.runner', return_value=failed):
            self.assertIsNone(quick_process.research(self.db, self.root, self.client, self.token))
        self.assertEqual(self.db.execute('SELECT searches FROM quick_checks').fetchone()[0], 4)
        self.assertIsNotNone(provider_health.blocked(self.db))

    def test_partial_final_line_keeps_completed_native_usage(self):
        value = native_search_trace.usage(self.search_log + b'\n{"partial":')
        self.assertEqual(len(value['queries']), 4)
        self.assertEqual(value['unfinished'], [])
