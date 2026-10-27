"""Different focals share one response scan without sharing mutable proof objects."""
import json
from unittest import TestCase
from unittest.mock import patch

from x_curator import x_detail, x_posts, x_response_index


def response():
    return {'data': [{'__typename': 'Tweet', 'rest_id': str(i),
                      'legacy': {'full_text': 'Response index fixture '+str(i)}} for i in range(12)]}


class ResponseIndexTests(TestCase):
    def test_many_focals_scan_original_bytes_once(self):
        body = json.dumps(dict(response(), scan_fixture=True)).encode()
        x_detail.authenticated.cache_clear()
        x_response_index.indexed.cache_clear()
        with patch.object(x_posts, 'nodes', wraps=x_posts.nodes) as scan:
            for i in range(12):
                focal, recovered = x_detail.validate(body, str(i))
                self.assertEqual(focal['rest_id'], str(i))
                self.assertEqual(len(recovered), 12)
        self.assertEqual(scan.call_count, 1)

    def test_changed_bytes_and_mutated_results_cannot_poison_another_focal(self):
        raw = response()
        body = json.dumps(raw).encode()
        focal, recovered = x_detail.validate(body, '0')
        focal['legacy']['full_text'] = 'Injected mutation'
        self.assertNotIn('Injected', recovered[0]['legacy']['full_text'])
        recovered[1]['legacy']['full_text'] = 'Injected mutation'
        self.assertNotIn('Injected', x_detail.validate(body, '1')[0]['legacy']['full_text'])
        raw['data'][1]['legacy']['full_text'] = 'Changed authentic bytes'
        self.assertEqual(x_detail.validate(json.dumps(raw).encode(), '1')[0]['legacy']['full_text'],
                         'Changed authentic bytes')

    def test_negative_focal_and_ambiguous_copies_still_veto_positive_objects(self):
        for negative in ({'__typename': 'TweetTombstone', 'rest_id': '1'},
                         {'entryId': 'tweet-1', 'content': {}},
                         {'entryId': 'tweet-1', 'content': {}, '__typename': 'TweetUnavailable', 'rest_id': '2'}):
            raw = response()
            raw['data'].append(negative)
            with self.assertRaises(x_posts.AmbiguousPost):
                x_detail.validate(json.dumps(raw).encode(), '1')
        raw = response()
        raw['data'].append(dict(raw['data'][1], legacy={'full_text': 'Conflicting copy'}))
        with self.assertRaises(x_posts.AmbiguousPost):
            x_detail.validate(json.dumps(raw).encode(), '1')

    def test_differing_entry_and_rest_ids_preserve_original_negative_predicate(self):
        raw = response()
        raw['data'].append({'entryId': 'tweet-1', '__typename': 'TweetUnavailable', 'rest_id': '2'})
        body = json.dumps(raw).encode()
        for identity in ('1', '2'):
            self.assertTrue(x_posts.negative(raw, identity))
            with self.assertRaises(x_posts.AmbiguousPost):
                x_detail.validate(body, identity)
