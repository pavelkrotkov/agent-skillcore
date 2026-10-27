from copy import deepcopy
from unittest.mock import patch
import time
import sqlite3

from x_article_recovery_fixtures import ArticleRecoveryCase
from x_curator import article_refresh, article_refresh_store as store, intake_store
from x_curator.publication_recovery import complete
from x_curator.source_evidence import selected_source


class ArticleRefreshTests(ArticleRecoveryCase):
    def permit(self):
        self.sparse()
        with patch('x_curator.article_qualification_store.XClient', return_value=self.detail_client()):
            complete(self.db, self.root, self.identity, 'Original one-off approval', refresh_article=True)
        store.enable(self.db, self.identity, 'Explicit recurring currentness approval')
        self.sparse()
        intake_store.initialize(self.db)
        current = selected_source(self.db, dict(account=self.detail_client().account, id='1'))
        with self.db:
            self.db.execute('INSERT INTO intake_runs VALUES (?,?,?,?,NULL)',
                            (current['run'], '[]', 100, time.time() + 300))
        return current

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

    def test_deadline_budget_and_wrong_account_reject_before_http(self):
        current = self.permit()
        client = self.detail_client()
        for sql in ('UPDATE intake_runs SET deadline=0',
                    'UPDATE intake_runs SET deadline=9999999999,request_limit=1'):
            with self.db:
                self.db.execute(sql)
            self.assertEqual(article_refresh.run(self.db, self.root, client)[0]['state'], 'held')
        with self.db:
            self.db.execute('UPDATE intake_runs SET request_limit=100')
        client.account = 'another-account'
        self.assertEqual(article_refresh.run(self.db, self.root, client)[0]['state'], 'held')
        client.detail.assert_not_called()
        self.assertEqual(self.db.execute('SELECT count(*) FROM article_refresh_requests').fetchone()[0], 0)

    def test_interrupted_reservation_is_spent_and_default_is_disabled(self):
        self.sparse()
        store.initialize(self.db)
        client = self.detail_client()
        self.assertEqual(article_refresh.run(self.db, self.root, client), [])
        client.detail.assert_not_called()
        with self.assertRaises(ValueError):
            store.enable(self.db, self.identity, 'No prior recovered article')

    def test_interruption_leaves_reservation_spent_with_no_http_on_restart(self):
        current = self.permit()
        client = self.detail_client()
        store.reserve(self.db, self.identity, current, client.account)
        self.assertEqual(article_refresh.run(self.db, self.root, client)[0]['state'], 'held')
        client.detail.assert_not_called()
        self.assertIsNone(self.db.execute('SELECT outcome FROM article_refresh_requests').fetchone()[0])

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
