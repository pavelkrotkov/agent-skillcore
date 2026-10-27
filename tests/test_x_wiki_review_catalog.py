from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator.receipts import digest
from x_curator.wiki_catalog import prepare
from x_curator.wiki_keys import page_key
from x_curator.wiki_mapping import organize
from x_curator.wiki_mapping_receipts import verified
from x_curator.wiki_review_catalog import review_keys


class ReviewCatalogTests(WikiCase):
    def test_authenticated_review_recovers_omitted_topic_without_extra_attempts(self):
        pages = [dict(self.mapping['pages'][0], title=title, description='x' * 60000, aliases=[])
                 for title in ('Synthetic evidence', 'ZZ unrelated')]
        pages = {page_key(page): page for page in pages}
        self.inputs = prepare(self.sources, pages, [self.publication])
        target = next(key for key, page in pages.items() if page['title'] == 'ZZ unrelated')
        rejected = self.reject_mapping('Reuse the existing concept “ZZ unrelated.”, not “Unknown page.”')
        self.assertEqual(review_keys(self.db, dict(self.inputs, catalog_sha='changed'), pages), set())
        self.mapping['pages'] = [pages[target]]
        with patch('x_curator.wiki_mapping.runner', side_effect=lambda *args: self.feedback_response):
            self.assertIsNone(organize(self.db, self.sources, pages, [self.publication]))
        row = self.db.execute("SELECT * FROM wiki_runs WHERE state='accepted'").fetchone()
        inputs, _ = verified(row)
        self.assertEqual(page_key(inputs['catalog'][0]), target)
        self.assertNotEqual(digest(inputs), digest(self.inputs))
        self.assertEqual(self.db.execute('SELECT attempts FROM wiki_sources').fetchone()[0], 2)
        self.assertEqual(self.db.execute('SELECT count(*) FROM wiki_recovery_grants').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT state FROM wiki_runs WHERE id=?', (rejected['id'],)).fetchone()[0], 'failed')
