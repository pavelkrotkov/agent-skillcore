import time
from unittest.mock import patch

from x_batch_fixtures import BatchCase
from x_fixtures import Client, collect, envelope, tweet_entry
from x_curator import daily_store


class DailyCase(BatchCase):
    def setUp(self):
        super().setUp()
        self.baseline = time.time() - 100
        self.cutoff = self.baseline + 50
        with self.db:
            self.db.execute('UPDATE jobs SET created=?', (self.baseline - 1,))
        with patch('x_curator.daily_store.time.time', return_value=self.baseline):
            daily_store.configure(self.db, Client.account, 'synthetic-chat', 'America/New_York')

    def intake(self, identities, captured):
        entries = [tweet_entry(str(i)) for i in identities]
        with patch('x_curator.collection_store.time.time', return_value=captured):
            return collect(self.db, Client([(200, envelope([{'type': 'TimelineAddEntries', 'entries': entries}]))]), 'likes', new=True, delay=0)

    def daily_work(self, limit=100):
        with patch('x_curator.daily_plan.cutoff', return_value=self.cutoff):
            return self.run_batch(limit)
