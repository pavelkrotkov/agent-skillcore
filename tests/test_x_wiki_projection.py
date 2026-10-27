from copy import deepcopy
from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator.wiki_catalog import prepare
from x_curator.wiki_keys import page_key
from x_curator.wiki_mapping import map_sources
from x_curator.wiki_mapping_receipts import verified
from x_curator.receipts import digest
from x_curator.wiki_notes import evidence


class WikiProjectionTests(WikiCase):
    def test_projection_preserves_all_prose_and_canonical_sources(self):
        original = deepcopy(self.sources)
        page = dict(self.mapping['pages'][0], aliases=[])
        inputs = prepare(self.sources, {page_key(page): page}, [self.publication])
        canonical = self.sources[self.publication]['packet']['claims'][0]
        expected = {key: value for key, value in canonical.items() if key != 'citations'}
        self.assertEqual(inputs['sources'][self.publication]['packet']['claims'], [expected])
        self.assertEqual(inputs['catalog'][0]['evidence'][0], dict(reference=page['claims'][0]))
        self.assertEqual(evidence(inputs)[(self.publication, 'c1')], expected)
        self.assertEqual(self.sources, original)
        self.assertEqual(inputs['publications_sha'], digest(original))
        projected = inputs['sources'][self.publication]['packet']
        self.assertEqual(dict(projected, claims=original[self.publication]['packet']['claims']), original[self.publication]['packet'])

    def test_legacy_full_citation_mapping_still_verifies(self):
        self.inputs.pop('projection')
        self.inputs.pop('catalog_projection')
        self.inputs.pop('final_format')
        self.inputs['sources'][self.publication]['packet'] = self.sources[self.publication]['packet']
        self.mapping['input_sha'] = digest(self.inputs)
        with patch('x_curator.wiki_mapping.runner', return_value=self.model):
            identity = map_sources(self.db, self.inputs)
        inputs, packet = verified(self.db.execute('SELECT * FROM wiki_runs WHERE id=?', (identity,)).fetchone())
        self.assertEqual(inputs, self.inputs)
        self.assertEqual(packet, self.mapping)
