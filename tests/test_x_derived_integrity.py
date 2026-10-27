import json
import time
from copy import deepcopy
from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_derived_fixtures import CHILD, ROOT, details, fetch, response
from x_curator.acquire import acquire_urls
from x_curator.evidence import bundle
from x_curator.receipts import digest, encoded
from x_curator import blobs, x_detail, x_derived


class DerivedIntegrityTests(PublicationCase):
    def test_parent_and_derived_fields_are_revalidated_not_trusted(self):
        acquire_urls(self.db, self.token, {ROOT}, fetch)
        evidence = bundle(self.db, self.token)
        key, original = details(evidence)[CHILD]
        for changes in ({'text': 'Invented prose'}, {'focal_id': '3'}, {'derivation_retrieval': 'missing'},
                        {'derived_from': key}, {'derived_from': 'other-attempt'}, {'fetched': time.time()}):
            with self.subTest(changes=changes):
                payload = dict(original, **changes)
                with self.db:
                    self.db.execute('UPDATE captures SET payload=?,sha=? WHERE id=?',
                                    (encoded(payload).decode(), digest(payload), key))
                with self.assertRaises((ValueError, KeyError)):
                    bundle(self.db, self.token)
        with self.db:
            self.db.execute('UPDATE captures SET payload=?,sha=? WHERE id=?',
                            (encoded(original).decode(), digest(original), key))
            self.db.execute("UPDATE retrievals SET url='https://x.com/i/status/999'")
        with self.assertRaisesRegex(ValueError, 'authenticated detail retrieval'):
            bundle(self.db, self.token)

    def test_only_typed_unambiguous_focals_can_be_derived(self):
        raw = json.loads(response())
        post = raw['data'][-1]['tweet']
        raw['data'].append(dict(post, legacy={'full_text': 'Conflicting post text'}))
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            x_detail.validate(json.dumps(raw).encode(), '2')
        raw['data'] = [raw['data'][0]]
        with self.assertRaisesRegex(ValueError, 'absent'):
            x_detail.validate(json.dumps(raw).encode(), '2')
        for raw in ({'__typename': 'Tweet', 'rest_id': '2'},
                    {'__typename': 'TweetWithVisibilityResults', 'tweet': None}):
            with self.assertRaisesRegex(ValueError, 'absent'):
                x_detail.validate(json.dumps(raw).encode(), '2')

    def test_stale_or_unproven_response_does_not_skip_a_request(self):
        acquire_urls(self.db, self.token, {ROOT}, fetch)
        evidence = bundle(self.db, self.token)
        with patch('x_curator.x_derived.time.time', return_value=time.time() + 86401):
            self.assertIsNone(x_derived.find(self.db, evidence, CHILD))
        with self.db:
            self.db.execute('UPDATE retrievals SET status=403')
        self.assertIsNone(x_derived.find(self.db, evidence, CHILD))

    def test_conflicting_parent_snapshots_are_not_used_for_derivation(self):
        acquire_urls(self.db, self.token, {ROOT}, fetch)
        evidence = bundle(self.db, self.token)
        parent_id, parent = details(evidence)[ROOT]
        changed = deepcopy(parent)
        changed['body_sha'] = blobs.put(self.db,
            response().replace(b'Complete synthetic long post.', b'A different synthetic long post.'))
        evidence['captures']['different-response'] = changed
        with patch('x_curator.x_derived_receipts.retrieval', return_value='proven-request'):
            self.assertIsNone(x_derived.find(self.db, evidence, CHILD))
        self.assertIn(parent_id, evidence['captures'])

    def test_visibility_wrapper_accepts_typeless_tweet_but_rejects_explicit_tombstone(self):
        raw = json.loads(response())
        post = raw['data'][-1]['tweet']
        post.pop('__typename')
        focal, _ = x_detail.validate(json.dumps(raw).encode(), '2')
        self.assertEqual(focal['rest_id'], '2')
        for kind in ('TweetTombstone', 'TweetUnavailable', 'Unknown'):
            post['__typename'] = kind
            with self.assertRaises(ValueError):
                x_detail.validate(json.dumps(raw).encode(), '2')
