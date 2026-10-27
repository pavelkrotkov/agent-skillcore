from copy import deepcopy

from x_wiki_fixtures import WikiCase
from x_curator.receipts import digest, encoded
from x_curator.wiki_catalog import prepare
from x_curator.wiki_contract import validate
from x_curator.wiki_keys import page_key
from x_curator import wiki_prompts


class WikiCatalogCapacityTests(WikiCase):
    def test_large_catalog_is_bounded_without_truncating_selected_claims(self):
        pages = {page_key(page): page for page in (dict(self.mapping['pages'][0], title=f'Topic {i:03}', aliases=[]) for i in range(50))}
        for page in pages.values():
            page['description'] = 'Synthetic background. ' * 1000
        original = deepcopy(self.sources)
        inputs = prepare(self.sources, pages, [self.publication])
        self.assertGreater(len(inputs['catalog']), 0)
        self.assertLess(len(inputs['catalog']), len(pages))
        self.assertLessEqual(len(encoded(inputs['catalog']).decode()) - 2, 100000)
        self.assertEqual(inputs['sources'], self.inputs['sources'])
        self.assertEqual(self.sources, original)
        self.assertEqual(inputs['known_keys'], sorted(pages))
        self.assertEqual(inputs['catalog_sha'], digest(pages))
        self.assertEqual(inputs['publications_sha'], digest(original))
        wiki_prompts.preflight(inputs)
        packet = dict(self.mapping, input_sha=digest(inputs), pages=[pages[sorted(pages)[-1]]])
        with self.assertRaisesRegex(ValueError, 'meaning was absent'):
            validate(packet, inputs)
