from copy import deepcopy
from unittest.mock import patch
import unittest
import json

from x_fixtures import CollectionCase, Client, response
from x_curator.collect import collect
from x_curator import source_evidence, source_authentication, model_trace, x_detail
from x_trace_fixtures import trace_fixture, rollout
from x_curator.worker_prompts import prompt
from x_curator.storage import sha256


class SharedSelectionTests(CollectionCase):
    def test_two_likes_share_one_authentic_response_parse(self):
        collect(self.db, Client([(200, response(('101', '102')))]), 'likes', limit=1, delay=0)
        with patch.object(source_authentication, 'parse', wraps=source_authentication.parse) as parse:
            first = source_evidence.selected_source(self.db, dict(account=Client.account, id='101'))
            source_evidence.selected_source(self.db, dict(account=Client.account, id='102'))
            first['entry'].clear()
            self.assertTrue(source_evidence.selected_source(self.db, dict(account=Client.account, id='101'))['entry'])
        self.assertEqual(parse.call_count, 1)

    def test_cached_response_does_not_bless_changed_selection_or_body(self):
        collect(self.db, Client([(200, response(('103',)))]), 'likes', limit=1, delay=0)
        job = dict(account=Client.account, id='103')
        source_evidence.selected_source(self.db, job)
        self.db.execute("UPDATE selections SET entry='{}' WHERE id='103'")
        with self.assertRaisesRegex(ValueError, 'authentic response'):
            source_evidence.selected_source(self.db, job)
        body = response(('104',))
        self.db.execute('UPDATE responses SET body=?,sha256=?', (body, sha256(body)))
        with self.assertRaisesRegex(ValueError, 'authentic response'):
            source_evidence.selected_source(self.db, job)


class SharedTranscriptTests(unittest.TestCase):
    def test_same_bytes_reuse_verification_without_sharing_mutable_output(self):
        request, events, rows = trace_fixture()
        proof = model_trace.pack(request, prompt(request), ['synthetic'], events, rollout(rows))
        with patch('x_curator.rollout_guard.verify', wraps=__import__('x_curator.rollout_guard', fromlist=['verify']).verify) as verify:
            first = model_trace.native(proof)
            expected = deepcopy(first)
            first.clear()
            self.assertEqual(model_trace.native(proof), expected)
            model_trace.verify_request(proof, request)
        self.assertEqual(verify.call_count, 0)

    def test_deep_post_traversal_is_iterative_and_preserves_order(self):
        leaf = {'__typename': 'Tweet', 'rest_id': 'leaf'}
        value = leaf
        for _ in range(1500):
            value = [value]
        self.assertEqual(list(source_evidence.nodes(value)), [leaf])
        root = {'left': [{'id': 'first'}], 'right': {'id': 'second'}}
        self.assertEqual(list(source_evidence.nodes(root)), [root, root['left'][0], root['right']])

    def test_detail_derivations_reuse_exact_bytes_and_isolate_caller_mutation(self):
        body = json.dumps({'data': {'__typename': 'Tweet', 'rest_id': '9918847722110000001', 'legacy': {'full_text': 'Synthetic.'}}}).encode()
        x_detail.authenticated.cache_clear()
        x_detail.indexed.cache_clear()
        with patch.object(x_detail, 'indexed', wraps=x_detail.indexed) as check:
            focal, _ = x_detail.validate(body, '9918847722110000001')
            focal.clear()
            self.assertEqual(x_detail.validate(body, '9918847722110000001')[0]['rest_id'], '9918847722110000001')
        self.assertEqual(check.call_count, 1)

    def test_cached_detail_preserves_original_key_order_for_historical_text(self):
        post = {'__typename': 'Tweet', 'rest_id': '9918847722110000002', 'legacy': {'user_id_str': 'author', 'full_text': 'Post text.'}}
        body = json.dumps({'data': post}).encode()
        expected = '\n'.join(source_evidence.strings(post))
        self.assertEqual(x_detail.extract(body, post['rest_id'])['text'], expected)
        self.assertEqual(x_detail.extract(body, post['rest_id'])['text'], expected)
