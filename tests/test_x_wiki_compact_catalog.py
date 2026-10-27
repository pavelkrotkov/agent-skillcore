from copy import deepcopy
from unittest import TestCase

from x_fixtures import SCRIPTS
from x_curator.receipts import digest
from x_curator.wiki_catalog import prepare
from x_curator.wiki_contract import validate
from x_curator.wiki_keys import page_key
from x_curator.wiki_notes import evidence


class CompactCatalogTests(TestCase):
    def setUp(self):
        self.refs = [dict(publication='long-source', claim=str(i)) for i in range(2)]
        self.claims = [dict(id=str(i), text='Retained prose. ' * 5000, kind='opinion',
                            attribution='Synthetic author', limitations=['Not independently established.']) for i in range(2)]
        self.current = {'long-source': {'packet': {'claims': self.claims}}}
        self.pages = [dict(kind='concept', title=f'Concept {i}', description='Distinct scope.', aliases=[],
                           claims=[ref], related=[], synthesis=[dict(text='Attributed opinion.', claims=[ref])])
                      for i, ref in enumerate(self.refs)]

    def test_long_required_catalog_keeps_exact_evidence_without_repeating_prose(self):
        catalog = {page_key(page): page for page in self.pages}
        original = deepcopy(self.current)
        inputs = prepare(self.current, catalog, ['long-source'], list(catalog))
        self.assertEqual(len(inputs['catalog']), 2)
        self.assertEqual(evidence(inputs), {('long-source', str(i)): claim for i, claim in enumerate(self.claims)})
        self.assertEqual(self.current, original)
        self.assertEqual(inputs['catalog'][0]['evidence'][0].keys(), {'reference'})
        validate(dict(input_sha=digest(inputs), pages=self.pages), inputs)

    def test_old_inline_catalog_and_nonselected_context_keep_complete_prose(self):
        ref = dict(publication='other', claim='old')
        item = dict(id='old', text='Other retained claim.', kind='opinion', reference=ref)
        old = dict(catalog=[dict(evidence=[item])])
        self.assertEqual(evidence(old), {('other', 'old'): item})
        old.update(catalog_projection=2, sources=self.current)
        self.assertEqual(evidence(old), {('other', 'old'): item})

    def test_missing_selected_reference_fails_closed(self):
        item = dict(reference=dict(publication='long-source', claim='missing'))
        inputs = dict(catalog_projection=2, sources=self.current, catalog=[dict(evidence=[item])])
        with self.assertRaises(KeyError):
            evidence(inputs)
