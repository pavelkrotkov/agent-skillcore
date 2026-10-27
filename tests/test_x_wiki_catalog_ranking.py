from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator.receipts import digest, encoded
from x_curator.wiki_catalog import catalog_page, prepare
from x_curator.wiki_contract import validate
from x_curator.wiki_keys import claim_index, page_key


class WikiCatalogRankingTests(WikiCase):
    def test_named_entity_precedes_verbose_background_when_only_one_page_fits(self):
        claim = self.sources[self.publication]['packet']['claims'][0]
        claim['text'] = 'Use vLLM for inference; consider latency throughput memory architecture.'
        entity = dict(self.mapping['pages'][0], kind='entity', title='vLLM', aliases=[])
        background = dict(entity, title='Other runtime', description=claim['text'])
        pages = {page_key(page): page for page in (background, entity)}
        allowance = len(encoded(catalog_page(entity, claim_index(self.sources), [self.publication])).decode())
        with patch('x_curator.wiki_catalog.preflight', return_value=allowance):
            inputs = prepare(self.sources, pages, [self.publication])
        self.assertEqual([page['title'] for page in inputs['catalog']], ['vLLM'])
        validate(dict(self.mapping, input_sha=digest(inputs), pages=[entity]), inputs)
