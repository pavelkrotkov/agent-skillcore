import json
from copy import deepcopy

from x_quick_context_fixtures import ContextCase
from x_thread_fixtures import post
from x_curator import x_detail
from x_curator.publication_audit import audit


def views():
    reference = post('2', 'a', '1', quoted_status_id_str='5')
    reference['legacy']['full_text'] = 'I recommend keeping a notebook.'
    reference['quotedRefResult'] = {'result': {'__typename': 'Tweet', 'rest_id': '5'}}
    expanded = deepcopy(reference)
    del expanded['quotedRefResult']
    expanded['quoted_status_result'] = {'result': post('5', 'b', '5')}
    return reference, expanded


class QuotedViewTests(ContextCase):
    def test_thread_capture_uses_original_expanded_view_and_authentic_parent(self):
        reference, expanded = views()
        self.posts[1] = reference
        self.posts.append(expanded)
        self.assertEqual(self.run_worker()['completed'], 1)
        self.client.detail.assert_called_once_with('1')
        captures = self.request['bundle']['captures']
        child = next(c for c in captures.values() if c.get('focal_id') == '2')
        parent = captures[child['derived_from']]
        self.assertEqual(child['body_sha'], parent['body_sha'])
        self.assertIn('Synthetic context evidence.', child['text'])
        self.assertEqual(audit(self.db, self.root), [])
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 0)

    def test_matching_views_select_original_expansion_in_either_order(self):
        reference, expanded = views()
        for posts in ([reference, expanded], [expanded, reference]):
            focal, _ = x_detail.validate(json.dumps({'data': posts}).encode(), '2')
            self.assertEqual(focal, expanded)

    def test_real_quote_and_reply_conflicts_remain_ambiguous(self):
        reference, expanded = views()
        wrong_text = deepcopy(reference)
        wrong_text['legacy']['full_text'] = 'A different reply.'
        wrong_identity = deepcopy(reference)
        wrong_identity['quotedRefResult']['result']['rest_id'] = '6'
        nonbare = deepcopy(reference)
        nonbare['quotedRefResult']['result']['legacy'] = {'full_text': 'Conflicting quote.'}
        wrong_body = deepcopy(expanded)
        wrong_body['quoted_status_result']['result']['legacy']['full_text'] = 'Conflicting quote.'
        both = deepcopy(wrong_body)
        both['quotedRefResult'] = reference['quotedRefResult']
        malformed = dict(reference, quoted_status_result='unavailable')
        for other in (wrong_text, wrong_identity, nonbare, wrong_body, both, malformed):
            with self.subTest(other=other), self.assertRaisesRegex(ValueError, 'ambiguous'):
                x_detail.validate(json.dumps({'data': [expanded, other]}).encode(), '2')
