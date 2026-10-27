import json
import time
from unittest.mock import patch

from x_quick_fixtures import QuickCase
from x_curator import quick_mcp, quick_store, quick_sources, quick_web
from x_curator.leases import fail, claim
from x_fixtures import Client


class QuickBudgetTests(QuickCase):
    def test_fourth_query_and_new_process_retry_cannot_replenish_allowance(self):
        quick_store.start(self.db, self.token, time.time())
        with patch('x_curator.quick_search.fetch', self.fetch):
            for _ in range(3):
                self.assertFalse(quick_mcp.call(self.db, self.token, 'search', {'query': 'synthetic'})['isError'])
            self.assertTrue(quick_mcp.call(self.db, self.token, 'search', {'query': 'fourth'})['isError'])
            fail(self.db, self.token, 'synthetic interruption', retry_after=0)
            self.token = claim(self.db, Client.account)['token']
            resumed = quick_store.start(self.db, self.token, time.time())
            self.assertEqual(resumed['searches'], 3)
            self.assertTrue(quick_mcp.call(self.db, self.token, 'search', {'query': 'retry'})['isError'])
        self.assertEqual(len(self.calls), 3)

    def test_read_has_no_arbitrary_url_or_search_endpoint_bypass(self):
        quick_store.start(self.db, self.token, time.time())
        with patch('x_curator.quick_web.fetch', self.fetch):
            self.assertTrue(quick_mcp.call(self.db, self.token, 'read', {'source': 'https://example.test/unregistered'})['isError'])
            with self.assertRaises(ValueError):
                quick_sources.source(self.db, self.token, 'https://www.bing.com/search?q=extra')
            registered = quick_sources.source(self.db, self.token, 'https://example.test/')
            self.assertTrue(quick_mcp.call(self.db, self.token, 'read', {'source': registered, 'url': 'https://example.test/search'})['isError'])
        self.assertEqual(self.calls, [])

    def test_deadline_survives_restart_and_blocks_transport(self):
        original = quick_store.start(self.db, self.token, time.time() - 121)
        fail(self.db, self.token, 'synthetic interruption', retry_after=0)
        self.token = claim(self.db, Client.account)['token']
        resumed = quick_store.start(self.db, self.token, time.time())
        self.assertEqual(resumed['deadline'], original['deadline'])
        with patch('x_curator.quick_search.fetch', self.fetch):
            self.assertTrue(quick_mcp.call(self.db, self.token, 'search', {'query': 'late'})['isError'])
        self.assertEqual(self.calls, [])

    def test_private_redirects_and_media_do_not_launch_readers(self):
        quick_store.start(self.db, self.token, time.time())
        registered = quick_sources.source(self.db, self.token, 'https://example.test/')
        original = quick_web.fetch
        def response(url):
            return (302, 'text/html', b'', 'http://127.0.0.1/') if url == 'https://example.test/' else original(url)
        with patch('x_curator.quick_web.fetch', side_effect=response) as fetch:
            result = quick_mcp.call(self.db, self.token, 'read', {'source': registered})
            self.assertTrue(result['isError'])
            self.assertIn('private or reserved', result['content'][0]['text'])
            self.assertEqual(fetch.call_count, 2)
        with self.assertRaises(ValueError):
            quick_web.text(b'%PDF synthetic', 'application/pdf', 'https://example.test/book')
