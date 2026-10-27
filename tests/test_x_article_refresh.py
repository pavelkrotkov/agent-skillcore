from copy import deepcopy
import sqlite3
import time
from x_article_refresh_fixtures import ArticleRefreshCase
from x_curator import article_refresh, article_refresh_store as store
from x_curator.source_evidence import selected_source


class ArticleRefreshTests(ArticleRefreshCase):
    def test_renewal_preserves_original_proof_and_one_request_is_durable(self):
            current = self.permit()
            history = self.history()
            counters = tuple(self.db.execute('SELECT attempts,max_attempts FROM jobs').fetchone())
            client = self.detail_client()
            result = article_refresh.run(self.db, self.root, client)
            self.assertEqual(result[0]['state'], 'published')
            client.detail.assert_called_once_with('1')
            self.assertEqual(store.remaining(self.db, current['run']), 98)
            self.assertEqual(article_refresh.run(self.db, self.root, client), [])
            for table in ('attempts', 'executions', 'captures', 'retrievals'):
                self.assertEqual(self.history()[table], history[table])
            self.assertEqual(tuple(self.db.execute('SELECT attempts,max_attempts FROM jobs').fetchone()), counters)
            with self.assertRaises(sqlite3.IntegrityError):
                store.reserve(self.db, self.identity, current, client.account)
            client.detail.assert_called_once()

    def test_spent_failed_request_is_not_retried_and_changed_content_stays_held(self):
            self.permit()
            focal = deepcopy(self.focal)
            focal['article']['article_results']['result']['plain_text'] = 'Changed article'
            client = self.detail_client(focal)
            self.assertEqual(article_refresh.run(self.db, self.root, client)[0]['state'], 'held')
            self.assertEqual(article_refresh.run(self.db, self.root, client)[0]['state'], 'held')
            client.detail.assert_called_once()
            self.assertEqual(self.db.execute('SELECT state FROM publications').fetchone()[0], 'invalid')
            self.assertEqual(self.db.execute('SELECT count(*) FROM article_refresh_requests').fetchone()[0], 1)

    def test_new_collection_gets_one_fresh_budget_without_reusing_old_qualification(self):
            first = self.permit()
            client = self.detail_client()
            self.assertEqual(article_refresh.run(self.db, self.root, client)[0]['state'], 'published')
            self.sparse()
            current = selected_source(self.db, dict(account=client.account, id='1'))
            self.assertNotEqual(first['run'], current['run'])
            with self.db:
                self.db.execute('INSERT INTO intake_runs VALUES (?,?,?,?,NULL)',
                                (current['run'], '[]', 100, time.time() + 300))
            self.assertEqual(article_refresh.run(self.db, self.root, client)[0]['state'], 'published')
            self.assertEqual(client.detail.call_count, 2)
            self.assertEqual(self.db.execute('SELECT count(*) FROM article_refresh_requests').fetchone()[0], 2)
