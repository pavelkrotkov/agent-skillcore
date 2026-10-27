from unittest.mock import patch
import time
from x_article_recovery_fixtures import ArticleRecoveryCase
from x_curator import article_refresh_store as store, intake_store
from x_curator.publication_recovery import complete
from x_curator.source_evidence import selected_source


class ArticleRefreshCase(ArticleRecoveryCase):
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
