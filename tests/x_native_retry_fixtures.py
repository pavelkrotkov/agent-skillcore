"""Real native execution fixtures for malformed-stream retry accounting."""
from unittest.mock import patch

from x_fixtures import Client
from x_native_search_fixtures import NativeCase
from x_curator import batch_queue, provider_health, quick_process


class NativeRetryCase(NativeCase):
    def malformed(self, log):
        with patch('x_curator.quick_process.runner', return_value=lambda _: log):
            quick_process.research(self.db, self.root, self.client, self.token)
        check = dict(self.db.execute('SELECT * FROM quick_checks WHERE token=?', (self.token,)).fetchone())
        execution = dict(self.db.execute('SELECT * FROM executions WHERE token=?', (self.token,)).fetchone())
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'retry')
        self.assertEqual((execution['log'], execution['finished']), (log, None))
        self.assertEqual(check['outcome'], 'inconclusive')
        self.assertEqual(self.db.execute('SELECT count(*) FROM quick_retry_failures').fetchone()[0], 1)
        self.assertIsNone(provider_health.blocked(self.db))
        return check, execution

    def resume(self):
        next_at = self.db.execute('SELECT next_at FROM jobs').fetchone()[0]
        with patch('x_curator.batch_queue.time.time', return_value=next_at + 1):
            self.token = batch_queue.claim(self.db, Client.account)['token']
