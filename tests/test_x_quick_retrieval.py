import json
import time
from unittest.mock import patch

from x_quick_fixtures import QuickCase
from x_curator import quick_mcp, quick_sources, quick_store
from x_curator.quick_support import independent


class QuickRetrievalTests(QuickCase):
    def test_tracking_variant_suggests_registered_handle_without_granting_an_alias(self):
        quick_store.start(self.db, self.token, time.time())
        url = 'https://example.test/start?utm_source=search'
        source = quick_sources.source(self.db, self.token, url)
        with patch('x_curator.quick_web.fetch', return_value=(200, 'text/plain', b'Publisher evidence.', None)) as fetch:
            unknown = quick_mcp.call(self.db, self.token, 'read', {'source': 'https://example.test/start'})
            self.assertTrue(unknown['isError'])
            self.assertIn(source, unknown['content'][0]['text'])
            fetch.assert_not_called()
            known = quick_mcp.call(self.db, self.token, 'read', {'source': source})
            self.assertFalse(known['isError'])
            fetch.assert_called_once_with(url)

    def read(self, match=''):
        quick_store.start(self.db, self.token, time.time())
        source = quick_sources.source(self.db, self.token, 'https://example.test/start')
        return quick_mcp.call(self.db, self.token, 'read', {'source': source, 'match': match})

    def test_redirect_keeps_final_origin_and_missing_match_returns_bounded_start(self):
        body = b'Observed source body. ' * 1000
        replies = [(301, 'text/html', b'', 'https://publisher.test/article'), (200, 'text/plain', body, None)]
        with patch('x_curator.quick_web.fetch', side_effect=replies) as fetch:
            result = self.read('absent phrase')
        self.assertFalse(result['isError'])
        evidence = json.loads(result['content'][0]['text'])['evidence']
        self.assertEqual(evidence['url'], 'https://publisher.test/article')
        self.assertEqual(evidence['requested_url'], 'https://example.test/start')
        self.assertEqual(evidence['text'], body.decode()[:6000])
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(self.db.execute('SELECT count(*) FROM retrievals').fetchone()[0], 2)

    def test_redirect_loop_stops_after_four_accounted_requests(self):
        with patch('x_curator.quick_web.fetch', return_value=(302, 'text/html', b'', '/again')) as fetch:
            result = self.read()
        self.assertIn('three-redirect allowance', result['content'][0]['text'])
        self.assertEqual(fetch.call_count, 4)
        self.assertEqual(self.db.execute('SELECT count(*) FROM retrievals').fetchone()[0], 4)

    def test_redirect_cannot_turn_read_into_an_extra_search(self):
        with patch('x_curator.quick_web.fetch', return_value=(302, 'text/html', b'', 'https://www.bing.com./search?q=extra')) as fetch:
            result = self.read()
        self.assertIn('search engine URLs', result['content'][0]['text'])
        self.assertEqual(fetch.call_count, 1)

    def test_dns_terminal_dot_does_not_create_an_independent_origin(self):
        sources = [{'capture': 'a', 'origin': 'First label'}, {'capture': 'b', 'origin': 'Second label'}]
        captures = {'a': {'url': 'https://publisher.test/a', 'body_sha': 'first'},
                    'b': {'url': 'https://www.publisher.test./b', 'body_sha': 'second'}}
        self.assertEqual(independent(sources, captures), 1)

    def test_http_failure_reports_actual_status(self):
        with patch('x_curator.quick_web.fetch', return_value=(403, 'text/html', b'', None)):
            result = self.read()
        self.assertEqual(result['content'][0]['text'], 'quick source unavailable: HTTP 403')

    def test_registered_url_alias_reaches_same_body_without_allowing_foreign_urls(self):
        quick_store.start(self.db, self.token, time.time())
        url = 'https://example.test/start'
        quick_sources.source(self.db, self.token, url)
        with patch('x_curator.quick_web.fetch', return_value=(200, 'text/plain', b'Original publisher statement.', None)) as fetch:
            result = quick_mcp.call(self.db, self.token, 'read', {'source': url})
            self.assertFalse(result['isError'])
            foreign = quick_mcp.call(self.db, self.token, 'read', {'source': 'https://example.test/unlisted'})
            self.assertIn('source ID', foreign['content'][0]['text'])
            self.assertEqual(fetch.call_count, 1)
