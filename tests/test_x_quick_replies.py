from x_quick_context_fixtures import ContextCase
from x_thread_fixtures import post
from x_curator import x_derived
from x_curator.publication_audit import audit


class QuickReplyTests(ContextCase):
    def test_visible_direct_answers_keep_authorship_and_do_not_expand_reply_threads(self):
        replies = [post(str(100 + n), 'answerer', '1', in_reply_to_status_id_str='1') for n in range(20)]
        self.posts[1]['legacy']['in_reply_to_status_id_str'] = '1'
        self.posts.extend([replies[0], replies[0], self.posts[1]] + replies + [post('200', 'answerer', '1', in_reply_to_status_id_str='100'),
                                    post('201', 'other', 'wrong', in_reply_to_status_id_str='1')])
        self.assertEqual(self.run_worker()['completed'], 1)
        self.client.detail.assert_called_once_with('1')
        evidence = self.request['bundle']
        details = {c['url']: c for c in evidence['captures'].values() if c['kind'] == 'x_detail'}
        answers = set(details) - {'https://x.com/i/status/1', 'https://x.com/i/status/2'}
        self.assertEqual(answers, {'https://x.com/i/status/' + str(n) for n in range(100, 116)})
        self.assertIn('answerer', details['https://x.com/i/status/100']['text'])
        x_derived.verify(self.db, evidence)
        self.assertEqual(audit(self.db, self.root), [])
