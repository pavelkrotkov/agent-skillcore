import json
from unittest.mock import Mock

from x_publication_fixtures import PublicationCase
from x_derived_fixtures import CHILD, ROOT, fetch, response
from x_thread_fixtures import post
from x_curator.acquire import acquire, acquire_urls
from x_curator.evidence import bundle, save_capture
from x_curator.retrievals import retrieve
from x_curator import x_detail, x_derived


class LatestDerivedTests(PublicationCase):
    def test_newer_proven_context_replaces_a_superseded_direct_cache_without_http(self):
        acquire_urls(self.db, self.token, {ROOT}, fetch)
        cached = retrieve(self.db, self.token, CHILD, fetch)
        cached.update(x_detail.extract(response(), '2', ['a', '1']))
        raw = json.loads(response())
        raw['data'][-1]['tweet']['note_tweet']['note_tweet_results']['result']['text'] = 'Newer complete source text.'
        raw['data'].append(post('3', 'c', '3'))
        body = json.dumps(raw).encode()
        parent_url = 'https://x.com/i/status/3'
        parent_id = acquire(self.db, self.token, parent_url, lambda _: (200, 'application/json', body, None))
        proof = x_derived.find(self.db, bundle(self.db, self.token), CHILD, cached)
        self.assertEqual(proof['derived_from'], parent_id)
        self.assertEqual(proof['final_url'], parent_url)
        self.assertIn('Newer complete source text.', proof['text'])
        key = save_capture(self.db, self.token, proof)
        self.assertEqual(bundle(self.db, self.token)['captures'][key], proof)
        self.assertEqual(self.db.execute('SELECT count(*) FROM retrievals').fetchone()[0], 3)

    def test_old_untyped_cache_falls_back_to_a_verified_new_detail_fetch(self):
        old_body = json.dumps({'rest_id': '1', 'legacy': {'full_text': 'Old untyped response.'}}).encode()
        cached = retrieve(self.db, self.token, ROOT, lambda _: (200, 'application/json', old_body, None))
        cached.update(kind='x_detail', text='Old untyped response.', thread_scope=['a', '1'])
        fetcher = Mock(side_effect=fetch)
        key = acquire(self.db, self.token, ROOT, fetcher, cached)
        fetcher.assert_called_once_with(ROOT)
        self.assertNotEqual(bundle(self.db, self.token)['captures'][key]['body_sha'], cached['body_sha'])
