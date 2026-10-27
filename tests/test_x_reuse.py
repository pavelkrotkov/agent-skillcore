from unittest.mock import Mock

from x_publication_fixtures import PublicationCase
from x_fixtures import Client
from x_curator.acquire import acquire_urls
from x_curator.evidence import bundle, capture_selection
from x_curator.leases import claim, fail_owned
from x_curator.reuse import captures


class ReuseTests(PublicationCase):
    def test_retry_reuses_verified_bytes_with_original_time_and_no_new_http_request(self):
        url = 'https://example.test/source'
        fetch = Mock(return_value=(200, 'text/plain', b'Synthetic source evidence with enough readable text for acquisition.', None))
        acquire_urls(self.db, self.token, {url}, fetch)
        original = next(c for c in bundle(self.db, self.token)['captures'].values() if c['kind'] == 'text')
        fail_owned(self.db, self.token, 'model response needs repair', 0)
        token = claim(self.db, Client.account)['token']
        capture_selection(self.db, token)
        self.assertEqual(len(captures(self.db, token)), 1)
        acquire_urls(self.db, token, {url}, fetch)
        fetch.assert_called_once()
        reused = next(c for c in bundle(self.db, token)['captures'].values() if c['kind'] == 'text')
        self.assertEqual(reused['fetched'], original['fetched'])
        self.assertIn('reused_from', reused)
        self.assertEqual(self.db.execute('SELECT count(*) FROM retrievals').fetchone()[0], 1)

    def test_old_or_damaged_capture_is_not_reused(self):
        acquire_urls(self.db, self.token, {'https://example.test/source'},
                     lambda _: (200, 'text/plain', b'Synthetic source evidence with enough readable text for acquisition.', None))
        fail_owned(self.db, self.token, 'retry', 0)
        token = claim(self.db, Client.account)['token']
        capture_selection(self.db, token)
        self.assertEqual(captures(self.db, token, max_age=0), {})
        with self.db:
            self.db.execute("UPDATE captures SET sha='damaged' WHERE token=?", (self.token,))
        self.assertEqual(captures(self.db, token), {})
