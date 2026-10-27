from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator.receipts import digest
from x_curator.wiki_catalog import prepare
from x_curator.wiki_keys import page_key
from x_curator.wiki_mapping import map_sources, organize
from x_curator.wiki_mapping_receipts import verified
from x_curator.wiki_catalog_recovery import required_keys


class CatalogRecoveryTests(WikiCase):
    def test_normal_mapper_recovers_authenticated_omission_without_extra_allowance(self):
        pages = [dict(self.mapping['pages'][0], title=title, description='x' * 60000, aliases=[])
                 for title in ('Synthetic evidence', 'ZZ unrelated')]
        pages = {page_key(page): page for page in pages}
        self.inputs = prepare(self.sources, pages, [self.publication])
        target = next(key for key, page in pages.items() if page['title'] == 'ZZ unrelated')
        self.mapping['pages'] = [pages[target]]
        requests = []

        def model(request):
            requests.append(request)
            return self.feedback_response(request)

        with patch('x_curator.wiki_mapping.runner', return_value=model):
            with self.assertRaisesRegex(ValueError, 'meaning was absent'):
                map_sources(self.db, self.inputs)
            self.assertEqual(required_keys(self.db, self.inputs), {target})
            self.assertIsNone(organize(self.db, self.sources, pages, [self.publication]))
        inputs, _ = verified(self.db.execute("SELECT * FROM wiki_runs WHERE state='accepted'").fetchone())
        self.assertNotEqual(digest(inputs), digest(self.inputs))
        self.assertEqual(page_key(inputs['catalog'][0]), target)
        self.assertNotIn('feedback', inputs)
        self.assertEqual(len(requests), 3)
        self.assertEqual(self.db.execute('SELECT attempts FROM wiki_sources').fetchone()[0], 2)
        self.assertEqual(required_keys(self.db, dict(self.inputs, publications_sha='changed')), set())
