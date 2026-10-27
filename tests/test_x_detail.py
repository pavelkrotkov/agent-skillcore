import json
from types import SimpleNamespace

from x_publication_fixtures import PublicationCase
from x_curator.acquire import acquire_urls
from x_curator.x_urls import source_fetcher
from x_curator.blobs import read
from x_curator.evidence import bundle


class DetailTests(PublicationCase):
    def test_detail_links_and_parent_media_are_acquired_to_closure(self):
        posts = {
            '1': {'__typename': 'Tweet', 'rest_id': '1', 'legacy': {'full_text': 'Synthetic evidence.', 'in_reply_to_status_id_str': '2',
                  'entities': {'urls': [{'expanded_url': 'https://example.org/source'}]}}},
            '2': {'__typename': 'Tweet', 'rest_id': '2', 'legacy': {'full_text': 'Parent source.', 'extended_entities': {'media': [
                  {'type': 'photo', 'media_url_https': 'https://example.org/image.png'}]}}},
        }
        def fetch(url):
            if url.startswith('https://x.com/'):
                return 200, 'application/json', json.dumps(posts[url.rsplit('/', 1)[1]]).encode(), None
            return 200, 'text/plain', b'Linked evidence with sufficient content.', None
        acquire_urls(self.db, self.token, {'https://x.com/i/status/1'}, fetch)
        captured = {c['url'] for c in bundle(self.db, self.token)['captures'].values()}
        self.assertEqual(captured, {'https://x.com/i/status/1', 'https://x.com/i/status/2',
                                   'https://example.org/source', 'https://example.org/image.png'})

    def test_rejected_detail_preserves_http_response(self):
        for body in (b'{"errors":[{"message":"synthetic denial"}]}', b'not json'):
            client = SimpleNamespace(detail=lambda _: (200, body))
            with self.assertRaises(ValueError):
                acquire_urls(self.db, self.token, {'https://x.com/i/status/1'}, source_fetcher(client))
            row = self.db.execute('SELECT status,body_sha FROM retrievals ORDER BY started DESC LIMIT 1').fetchone()
            self.assertEqual(row['status'], 200)
            self.assertEqual(read(self.db, row['body_sha']), body)

    def test_redirect_to_x_expands_authenticated_detail_obligations(self):
        body = json.dumps({'__typename': 'Tweet', 'rest_id': '1', 'legacy': {'full_text': 'Synthetic evidence.',
                          'entities': {'urls': [{'expanded_url': 'https://example.org/primary'}]}}}).encode()
        def fetch(url):
            if url == 'https://example.org/short':
                return 302, 'text/plain', b'redirect', 'https://x.com/i/status/1'
            if url == 'https://x.com/i/status/1':
                return 200, 'application/json', body, None
            return 200, 'text/plain', b'Actual primary evidence from the expanded link.', None
        acquire_urls(self.db, self.token, {'https://example.org/short'}, fetch)
        captured = list(bundle(self.db, self.token)['captures'].values())
        detail = next(c for c in captured if c['url'] == 'https://example.org/short')
        self.assertEqual(detail['kind'], 'x_detail')
        self.assertIn('https://example.org/primary', {c['url'] for c in captured})
