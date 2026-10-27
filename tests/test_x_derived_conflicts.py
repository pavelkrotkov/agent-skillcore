import json
from unittest.mock import Mock

from x_publication_fixtures import PublicationCase
from x_derived_fixtures import CHILD, ROOT, fetch, response
from x_curator.acquire import acquire, acquire_urls
from x_curator.evidence import bundle
from x_curator.retrievals import retrieve
from x_curator import x_detail, x_derived


class DerivedConflictTests(PublicationCase):
    def test_retained_tombstone_vetoes_derivation_and_cached_copy_before_http(self):
        acquire_urls(self.db, self.token, {ROOT}, fetch)
        cached = retrieve(self.db, self.token, CHILD, fetch)
        cached.update(x_detail.extract(response(), '2', ['a', '1']))
        body = json.dumps({'data': {'tweetResult': {'result': {'__typename': 'TweetTombstone'}}}}).encode()
        retrieve(self.db, self.token, CHILD, lambda _: (200, 'application/json', body, None))
        evidence = bundle(self.db, self.token)
        self.assertIsNone(x_derived.find(self.db, evidence, CHILD))
        self.assertIsNone(x_derived.find(self.db, evidence, CHILD, cached))
        fetcher = Mock(side_effect=fetch)
        acquire(self.db, self.token, CHILD, fetcher, cached)
        fetcher.assert_called_once_with(CHILD)

    def test_conflicting_newer_response_cannot_disappear_as_a_missing_candidate(self):
        acquire_urls(self.db, self.token, {ROOT}, fetch)
        raw = json.loads(response())
        post = raw['data'][-1]['tweet']
        raw['data'].append(dict(post, legacy={'full_text': 'Conflicting newer copy'}))
        body = json.dumps(raw).encode()
        retrieve(self.db, self.token, 'https://x.com/i/status/3',
                 lambda _: (200, 'application/json', body, None))
        self.assertIsNone(x_derived.find(self.db, bundle(self.db, self.token), CHILD))

    def test_contextual_tombstone_blocks_reuse_without_a_direct_request(self):
        acquire_urls(self.db, self.token, {ROOT}, fetch)
        body = json.dumps({'data': {'entryId': 'tweet-2', 'content': {'itemContent': {
            'tweet_results': {'result': {'__typename': 'TweetTombstone'}}}}}}).encode()
        retrieve(self.db, self.token, 'https://x.com/i/status/3',
                 lambda _: (200, 'application/json', body, None))
        self.assertIsNone(x_derived.find(self.db, bundle(self.db, self.token), CHILD))
