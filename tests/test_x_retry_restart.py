"""Interrupted checks and changed source revisions never renew an old allowance."""
import time
from unittest.mock import patch

from x_fixtures import Client, collect, envelope, tweet_entry
from x_retry_fixtures import RetryCase
from x_curator import batch_queue, quick_process, quick_store


class RetryRestartTests(RetryCase):
    def test_interrupted_lease_retries_with_backoff_and_retained_deadline(self):
        old = quick_store.start(self.db, self.token, time.time())
        job = self.db.execute('SELECT * FROM jobs').fetchone()
        with patch('x_curator.batch_queue.time.time', return_value=job['lease_until'] + 1):
            self.assertIsNone(batch_queue.claim(self.db, Client.account))
        saved = dict(self.db.execute('SELECT * FROM quick_checks WHERE id=?', (old['id'],)).fetchone())
        self.assertEqual((saved['started'], saved['deadline']), (old['started'], old['deadline']))
        self.next_attempt()
        child = quick_store.start(self.db, self.token, time.time())
        self.assertNotEqual(child['id'], old['id'])
        self.assertEqual(dict(self.db.execute('SELECT * FROM quick_checks WHERE id=?', (old['id'],)).fetchone()), saved)

    def test_source_revision_change_holds_retry_without_reusing_old_allowance(self):
        old = self.failed()
        entry = tweet_entry('1')
        entry['content']['itemContent']['tweet_results']['result']['legacy'] = {'full_text': 'Changed source revision.'}
        collect(self.db, Client([(200, envelope([{'type': 'TimelineAddEntries', 'entries': [entry]}]))]),
                'likes', new=True, delay=0)
        self.next_attempt()
        with patch('x_curator.quick_process.runner', side_effect=AssertionError('changed revision must be held')):
            quick_process.research(self.db, self.root, self.client, self.token)
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'awaiting_review')
        self.assertEqual(dict(self.db.execute('SELECT * FROM quick_checks WHERE id=?', (old['id'],)).fetchone()), old)
        self.assertEqual(self.db.execute('SELECT count(*) FROM quick_checks').fetchone()[0], 1)
