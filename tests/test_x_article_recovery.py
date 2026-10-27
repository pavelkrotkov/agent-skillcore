from copy import deepcopy
from unittest.mock import patch

from x_article_recovery_fixtures import ArticleRecoveryCase
from x_curator import publication_audit
from x_curator.publication_recovery import complete


class ArticleRecoveryTests(ArticleRecoveryCase):
    def test_sparse_receipt_recovers_original_native_approval_without_models_or_attempts(self):
        self.sparse()
        before = self.history()
        budget = tuple(self.db.execute('SELECT attempts,max_attempts FROM jobs').fetchone())
        client = self.detail_client()
        with patch('x_curator.article_qualification_store.XClient', return_value=client), patch('x_curator.research.runner', side_effect=AssertionError('no source retry')):
            result = complete(self.db, self.root, self.identity, 'Exact article verified unchanged', refresh_article=True)
            self.assertFalse(result['already_completed'])
            self.assertEqual(publication_audit.audit(self.db, self.root), [])
        client.detail.assert_called_once_with('1')
        after = self.history()
        self.assertEqual({k: v for k, v in after.items() if k != 'publications'},
                         {k: v for k, v in before.items() if k != 'publications'})
        old, new = before['publications'][0], after['publications'][0]
        self.assertEqual(old[:8] + old[9:], new[:8] + new[9:])
        self.assertEqual(tuple(self.db.execute('SELECT attempts,max_attempts FROM jobs').fetchone()), budget)
        self.assertEqual(self.db.execute('SELECT count(*) FROM publication_currentness').fetchone()[0], 1)
        self.assertEqual(self.db.execute('SELECT count(*) FROM publication_reinstatements').fetchone()[0], 1)
        self.sparse()
        with self.assertRaisesRegex(ValueError, 'different collection'):
            complete(self.db, self.root, self.identity, 'Old qualification cannot cover a new capture')

    def test_changed_article_failed_http_and_substantive_post_edits_fail_closed(self):
        self.sparse()
        for key in ('plain_text', 'title', 'rest_id', 'metadata'):
            focal = deepcopy(self.focal)
            focal['article']['article_results']['result'][key] = 'Changed'
            with self.subTest(key=key), patch('x_curator.article_qualification_store.XClient', return_value=self.detail_client(focal)), self.assertRaises(ValueError):
                complete(self.db, self.root, self.identity, 'Reject changed article', refresh_article=True)
        with patch('x_curator.article_qualification_store.XClient', return_value=self.detail_client(status=503)), self.assertRaisesRegex(ValueError, 'after the collection'):
            complete(self.db, self.root, self.identity, 'Reject failed HTTP', refresh_article=True)
        focal = deepcopy(self.focal)
        focal['legacy']['full_text'] = 'Changed source text'
        with patch('x_curator.article_qualification_store.XClient', return_value=self.detail_client(focal)), self.assertRaisesRegex(ValueError, 'unchanged focal'):
            complete(self.db, self.root, self.identity, 'Reject changed focal', refresh_article=True)
        self.assertEqual(self.db.execute('SELECT state FROM publications').fetchone()[0], 'invalid')

    def test_fresh_detail_does_not_replace_original_native_approval(self):
        self.sparse()
        with self.db:
            self.db.execute("UPDATE executions SET log=X'00' WHERE role='review'")
        with patch('x_curator.article_qualification_store.XClient', return_value=self.detail_client()), self.assertRaises(ValueError):
            complete(self.db, self.root, self.identity, 'Original approval is still required', refresh_article=True)
        self.assertEqual(self.db.execute('SELECT state FROM publications').fetchone()[0], 'invalid')
