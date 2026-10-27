from copy import deepcopy
from unittest import TestCase

from x_zk_retained_fixtures import inputs_and_pages
from x_curator import wiki_zk_prompt
from x_curator.receipts import digest
from x_curator.wiki_contract import validate
from x_curator.wiki_retained_assignments import retained


class RetainedAssignmentTests(TestCase):
    def setUp(self):
        self.inputs, self.pages = inputs_and_pages()

    def packet(self):
        return dict(input_sha=digest(self.inputs), pages=deepcopy(self.pages[:1]))

    def test_refresh_keeps_optional_note_without_resubmission_or_historical_change(self):
        validate(self.packet(), self.inputs)
        historical = dict(self.inputs)
        del historical['retained_assignments']
        with self.assertRaisesRegex(ValueError, 'every verified source claim'):
            validate(dict(self.packet(), input_sha=digest(historical)), historical)
        expected = wiki_zk_prompt.ZK + wiki_zk_prompt.LINKS + wiki_zk_prompt.COMPACT
        self.assertEqual(wiki_zk_prompt.instructions(historical), expected)
        self.assertEqual(wiki_zk_prompt.instructions(self.inputs), expected + wiki_zk_prompt.RETAINED)

    def test_incomplete_or_uncovered_catalog_claim_still_requires_assignment(self):
        for change in ('incomplete', 'uncovered'):
            with self.subTest(change=change):
                inputs = deepcopy(self.inputs)
                optional = next(p for p in inputs['catalog'] if p['title'] == self.pages[1]['title'])
                if change == 'incomplete':
                    optional['complete'] = False
                else:
                    optional['evidence'] = []
                with self.assertRaisesRegex(ValueError, 'every verified source claim'):
                    validate(dict(self.packet(), input_sha=digest(inputs)), inputs)

    def test_rewritten_and_retired_notes_cannot_supply_unchanged_coverage(self):
        packet = self.packet()
        self.assertEqual(retained(self.inputs, packet['pages']), {('source', '1')})
        packet['pages'][0]['replaces'] = [self.pages[1]]
        self.assertEqual(retained(self.inputs, packet['pages']), set())
        with self.assertRaisesRegex(ValueError, 'complete reviewed evidence'):
            validate(packet, self.inputs)

    def test_opt_in_is_bound_to_explicit_refresh_identity_and_version(self):
        for change in ({'retained_assignments': 'catalog/v2'}, {'refresh': None}, {'organization': None}):
            inputs = dict(self.inputs, **change)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'retained assignment contract'):
                validate(dict(self.packet(), input_sha=digest(inputs)), inputs)
