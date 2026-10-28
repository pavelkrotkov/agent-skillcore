from copy import deepcopy
from unittest import TestCase
from x_zk_retained_fixtures import inputs_and_pages
from x_curator.receipts import digest
from x_curator.wiki_keys import page_key
from x_curator.wiki_contract import validate
from x_curator.wiki_retained_assignments import retained
from x_curator.wiki_retained_catalog import omitted
from x_curator import wiki_zk_prompt


class HiddenAssignmentTests(TestCase):
    def setUp(self):
        self.inputs,self.pages = inputs_and_pages()
        self.global_pages = {page_key(p):p for p in self.pages}
        self.inputs['catalog'] = self.inputs['catalog'][:1]
        self.inputs['retained_catalog_assignments'] = omitted(self.global_pages,self.inputs['catalog'],{'source'})
        self.packet = dict(input_sha=digest(self.inputs),pages=deepcopy(self.pages[:1]))

    def test_bounded_context_preserves_actual_omitted_assignments_without_new_targets(self):
        before = deepcopy(self.global_pages)
        validate(self.packet,self.inputs)
        self.assertEqual(retained(self.inputs,self.packet['pages']),{('source','1')})
        self.assertEqual(self.global_pages,before)
        self.assertEqual(omitted(self.global_pages,[],{'other'}),[])
        self.packet['pages'].append(deepcopy(self.pages[1]))
        with self.assertRaisesRegex(ValueError,'absent from reviewed catalog'):
            validate(self.packet,self.inputs)

    def test_retiring_omitted_note_cannot_use_its_unchanged_assignments(self):
        self.packet['pages'][0]['replaces'] = [self.pages[1]]
        self.assertEqual(retained(self.inputs,self.packet['pages']),set())
        with self.assertRaisesRegex(ValueError,'distinct reviewed catalog'):
            validate(self.packet,self.inputs)

    def test_legacy_v1_never_reinterprets_new_metadata_or_changes_its_prompt(self):
        old = dict(self.inputs,retained_assignments='catalog/v1')
        with self.assertRaisesRegex(ValueError,'every verified source claim'):
            validate(dict(self.packet,input_sha=digest(old)),old)
        self.assertEqual(wiki_zk_prompt.instructions(old),
                         wiki_zk_prompt.ZK+wiki_zk_prompt.LINKS+wiki_zk_prompt.COMPACT+wiki_zk_prompt.RETAINED)

    def test_hidden_assignment_does_not_authorize_a_relationship_target(self):
        page=self.packet['pages'][0]
        page['claims']+=self.pages[1]['claims']
        page['related']=[dict(kind=self.pages[1]['kind'],title=self.pages[1]['title'],
                              reason='Synthetic connection',claims=page['claims'])]
        with self.assertRaisesRegex(ValueError,'related page target is missing'):
            validate(self.packet,self.inputs)
