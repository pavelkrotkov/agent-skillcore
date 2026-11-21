"""Incomplete native executions retain observed search usage and raw evidence."""
from unittest.mock import patch

from x_native_search_fixtures import NativeCase
from x_curator import provider_health, quick_process
from x_curator.receipts import encoded


class NativeCompletionRetryTests(NativeCase):
    def test_missing_completion_retains_queries_without_opening_the_provider_circuit(self):
        log = encoded({'type': 'thread.started', 'thread_id': 'synthetic-session'}) + b'\n' + self.search_log
        with patch('x_curator.quick_process.runner', return_value=lambda _: log):
            quick_process.research(self.db, self.root, self.client, self.token)
        execution = self.db.execute('SELECT log,finished FROM executions').fetchone()
        check = self.db.execute('SELECT searches,reason FROM quick_checks').fetchone()
        self.assertEqual(tuple(execution), (log, None))
        self.assertEqual(check['searches'], 4)
        self.assertIn('ModelCompletionError', check['reason'])
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'retry')
        self.assertIsNone(provider_health.blocked(self.db))
