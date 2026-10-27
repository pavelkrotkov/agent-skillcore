
from x_wiki_fixtures import WikiCase
from x_curator.receipts import digest, encoded
from x_curator.wiki_catalog import prepare
from x_curator.wiki_contract import validate
from x_curator.wiki_keys import page_key
from x_curator import wiki_prompts


class RequiredCatalogTests(WikiCase):
    def pages(self):
        pages = [dict(self.mapping['pages'][0], title=f'Topic {i:03}', aliases=[]) for i in range(50)]
        return {page_key(page): page for page in pages}

    def test_required_current_meaning_recovers_target_beyond_bounded_prefix(self):
        pages = {key: dict(page, description='Context ' * 1000) for key, page in self.pages().items()}
        target = sorted(pages)[-1]
        original = prepare(self.sources, pages, [self.publication])
        self.assertNotIn(target, {page_key(page) for page in original['catalog']})
        inputs = prepare(self.sources, pages, [self.publication], [target])
        self.assertEqual(inputs['catalog'][0]['description'], pages[target]['description'])
        self.assertEqual(page_key(inputs['catalog'][0]), target)
        self.assertLessEqual(len(encoded(inputs['catalog']).decode()) - 2, 100000)
        wiki_prompts.preflight(inputs)
        packet = dict(self.mapping, input_sha=digest(inputs), pages=[dict(pages[target])])
        validate(packet, inputs)

    def test_unknown_and_oversized_required_meanings_fail_closed(self):
        pages = self.pages()
        with self.assertRaisesRegex(ValueError, 'page is unknown'):
            prepare(self.sources, pages, [self.publication], ['missing'])
        target = sorted(pages)[-1]
        pages[target]['description'] = 'x' * 100000
        with self.assertRaisesRegex(ValueError, 'exceeds catalog budget'):
            prepare(self.sources, pages, [self.publication], [target])

    def test_required_set_cannot_be_silently_truncated(self):
        pages = {key: dict(page, description='x' * 60000) for key, page in self.pages().items()}
        with self.assertRaisesRegex(ValueError, 'exceeds catalog budget'):
            prepare(self.sources, pages, [self.publication], sorted(pages)[:2])
