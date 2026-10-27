from copy import deepcopy
from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator.receipts import digest, encoded
from x_curator.wiki_catalog import prepare
from x_curator.wiki_contract import validate
from x_curator.wiki_keys import page_key
from x_curator import wiki_prompts
from x_curator.wiki_prompt_payload import payload


class WikiCatalogTests(WikiCase):
    def pages(self):
        pages = [dict(self.mapping['pages'][0], title=f'Topic {i:03}', aliases=[]) for i in range(50)]
        return {page_key(page): page for page in pages}

    def test_existing_page_after_fortieth_is_available_when_full_catalog_fits(self):
        pages = self.pages()
        inputs = prepare(self.sources, pages, [self.publication])
        self.assertEqual(len(inputs['catalog']), 50)
        wiki_prompts.preflight(inputs)
        packet = deepcopy(self.mapping)
        packet['pages'] = [dict(pages[sorted(pages)[-1]])]
        packet['input_sha'] = digest(inputs)
        validate(packet, inputs)

    def test_conservative_review_boundary_keeps_ranked_prefix_and_collision_guard(self):
        pages = self.pages()
        full = prepare(self.sources, pages, [self.publication])
        base = dict(full, catalog=[])
        envelope = len(wiki_prompts.prompt(wiki_prompts.request('organize_review', base)))
        limit = envelope + wiki_prompts.PROPOSAL_LIMIT + len(encoded(full['catalog'][:2]).decode()) - 2
        with patch.object(wiki_prompts, 'LIMIT', limit):
            inputs = prepare(self.sources, pages, [self.publication])
            self.assertEqual(inputs['catalog'], full['catalog'][:2])
            visible = payload(wiki_prompts.request('organize_review', inputs))['bundle']['wiki_inputs']['catalog']
            saved = len(encoded(inputs['catalog']).decode()) - len(encoded(visible).decode())
            self.assertEqual(len(wiki_prompts.prompt(wiki_prompts.request('organize_review', inputs))) + wiki_prompts.PROPOSAL_LIMIT + saved, limit)
            packet = deepcopy(self.mapping)
            packet.update(input_sha=digest(inputs), pages=[dict(pages[sorted(pages)[-1]])])
            with self.assertRaisesRegex(ValueError, 'meaning was absent'):
                validate(packet, inputs)
