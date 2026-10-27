from x_article_refresh_fixtures import ArticleRefreshCase
from x_curator import article_refresh, article_refresh_store as store
from x_curator.source_evidence import selected_source


class ArticleRefreshBudgetTests(ArticleRefreshCase):
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
