import json
from unittest.mock import Mock, patch

from x_fixtures import Client
from x_publication_fixtures import PublicationCase
from x_thread_fixtures import ROOT, fetch
from x_curator import x_detail
from x_curator.acquire import acquire_urls
from x_curator.evidence import bundle, capture_selection
from x_curator.leases import claim, fail_owned


class ThreadReuseTests(PublicationCase):
    def test_prior_foreign_expansion_is_rederived_without_importing_unreachable_captures(self):
        fetcher = Mock(side_effect=fetch)
        with patch('x_curator.x_thread.selected_scope', side_effect=lambda db, token, body, requested: x_detail.scope(body, requested)):
            acquire_urls(self.db, self.token, {ROOT}, fetcher)
        original = bundle(self.db, self.token)
        self.assertIn('https://x.com/i/status/4', {c['url'] for c in original['captures'].values()})
        fail_owned(self.db, self.token, 'retry scoped extraction', 0)
        token = claim(self.db, Client.account)['token']
        capture_selection(self.db, token)
        calls = fetcher.call_count
        acquire_urls(self.db, token, {ROOT}, fetcher)
        current = bundle(self.db, token)['captures'].values()
        self.assertNotIn('https://x.com/i/status/4', {c['url'] for c in current})
        self.assertEqual(fetcher.call_count, calls)
        prior = original['captures']
        parent = next(c for c in current if c['url'].endswith('/3'))
        self.assertEqual(parent['fetched'], prior[parent['reused_from']]['fetched'])
        self.assertEqual(parent['extraction_policy'], 'selected-thread-v1')
        self.assertEqual(parent['thread_scope'], ['a', '1'])
        retained = self.db.execute('SELECT payload FROM captures WHERE id=?', (parent['reused_from'],)).fetchone()[0]
        self.assertEqual(json.loads(retained), prior[parent['reused_from']])
