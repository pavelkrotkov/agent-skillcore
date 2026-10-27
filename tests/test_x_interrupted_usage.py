from unittest.mock import patch

from x_native_search_fixtures import NativeCase
from x_curator import execution_failure, quick_process
from x_curator.deadlines import DeadlineExceeded
from x_curator.worker_errors import WorkerFailure


class InterruptedUsageTests(NativeCase):
    def interrupted(self, request):
        raise WorkerFailure('synthetic failure', log=self.search_log)

    def test_retained_log_replays_usage_without_overwriting_bytes(self):
        with patch('x_curator.quick_process.runner', return_value=self.interrupted), \
                patch('x_curator.native_search.record'):
            quick_process.research(self.db, self.root, self.client, self.token)
        self.assertEqual(self.db.execute('SELECT searches FROM quick_checks').fetchone()[0], 0)
        error = DeadlineExceeded('synthetic interrupted accounting')
        error.log = b'different fallback bytes'
        execution_failure.record(self.db, self.root, self.token, error)
        execution_failure.record(self.db, self.root, self.token, error)
        execution = self.db.execute('SELECT log,finished FROM executions').fetchone()
        self.assertEqual(tuple(execution), (self.search_log, None))
        self.assertEqual(self.db.execute('SELECT searches FROM quick_checks').fetchone()[0], 4)
