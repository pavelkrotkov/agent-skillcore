"""Shared finite retry fixture using the real dispatch and quick-check paths."""
from unittest.mock import patch

from x_fixtures import Client
from x_quick_fixtures import QuickCase
from x_curator import batch_queue, quick_process


class RetryCase(QuickCase):
    def failed(self):
        with patch('x_curator.quick_process.runner', side_effect=OSError('synthetic transport interruption')):
            quick_process.research(self.db, self.root, self.client, self.token)
        return dict(self.db.execute('SELECT * FROM quick_checks WHERE token=?', (self.token,)).fetchone())

    def next_attempt(self):
        job = self.db.execute('SELECT * FROM jobs').fetchone()
        self.assertIsNone(batch_queue.claim(self.db, Client.account))
        with patch('x_curator.batch_queue.time.time', return_value=job['next_at'] + 1):
            claimed = batch_queue.claim(self.db, Client.account)
        self.token = claimed['token']
        return claimed
