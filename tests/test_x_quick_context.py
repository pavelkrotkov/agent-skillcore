import json

from x_quick_context_fixtures import ContextCase
from x_curator import x_derived
from x_curator.publication_audit import audit


class QuickContextTests(ContextCase):
    def test_one_detail_request_supplies_only_selected_author_conversation(self):
        self.assertEqual(self.run_worker()['completed'], 1)
        self.assertFalse(self.validation['isError'], self.validation)
        self.client.detail.assert_called_once_with('1')
        evidence = self.request['bundle']
        details = {c['url']: c for c in evidence['captures'].values() if c['kind'] == 'x_detail'}
        self.assertEqual(set(details), {'https://x.com/i/status/1', 'https://x.com/i/status/2'})
        root, continuation = (details['https://x.com/i/status/' + n] for n in ('1', '2'))
        self.assertIn('Complete long note.', root['text'])
        self.assertEqual(root['body_sha'], continuation['body_sha'])
        receipt = self.db.execute('SELECT id,body_sha FROM retrievals').fetchone()
        self.assertEqual(tuple(receipt), (continuation['derivation_retrieval'], root['body_sha']))
        self.assertEqual(audit(self.db, self.root), [])
        self.assertEqual(self.db.execute('SELECT count(*) FROM executions').fetchone()[0], 1)
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 0)
        check = self.db.execute('SELECT * FROM quick_checks').fetchone()
        self.assertEqual(check['deadline'] - check['started'], 120)
        continuation['text'] += ' Forged continuation.'
        with self.assertRaisesRegex(ValueError, 'derived post differs'):
            x_derived.verify(self.db, evidence)

    def test_unavailable_detail_is_explicit_failure_before_model_launch(self):
        self.assertEqual(self.run_worker(json.dumps({'data': []}).encode())['completed'], 0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM executions').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM retrievals').fetchone()[0], 1)
        self.assertIn('focal', self.db.execute('SELECT reason FROM quick_checks').fetchone()[0])

    def test_missing_thread_scope_is_explicit_failure_before_model_launch(self):
        self.posts[0]['legacy'].pop('user_id_str')
        self.assertEqual(self.run_worker()['completed'], 0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM executions').fetchone()[0], 0)
        self.assertIn('author/conversation', self.db.execute('SELECT reason FROM quick_checks').fetchone()[0])
