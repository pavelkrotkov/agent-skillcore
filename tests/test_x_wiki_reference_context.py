from copy import deepcopy
from unittest import TestCase

from x_fixtures import SCRIPTS
from x_curator.receipts import digest
from x_curator.wiki_notes import request
from x_curator.wiki_prompt_payload import payload
from x_curator.wiki_references import canonical


class WikiReferenceContextTests(TestCase):
    def test_catalog_feedback_and_reviewer_share_collision_free_canonical_references(self):
        selected, neighbor = 'z' * 64, '@1'
        refs = [dict(publication=p, claim='c1') for p in (selected, neighbor)]
        catalog = [dict(evidence=[dict(reference=refs[1])], related=[dict(claims=refs)])]
        packet = dict(pages=[dict(claims=refs)])
        inputs = dict(publication_references='short/v1', sources={selected: dict(publication=selected)},
                      catalog=catalog, feedback=dict(proposal=packet))
        before = deepcopy(inputs)
        view = payload(request('organize_review', inputs, packet))
        visible = view['bundle']['wiki_inputs']
        self.assertEqual(set(visible['sources']), {'@@2'})
        self.assertEqual(visible['catalog'][0]['evidence'][0]['reference']['publication'], '@@1')
        self.assertEqual(canonical(visible['catalog'], inputs), catalog)
        self.assertEqual(canonical(visible['feedback']['proposal'], inputs), packet)
        self.assertEqual(canonical(view['proposal'], inputs), packet)
        self.assertEqual(view['proposal_sha'], digest(packet))
        self.assertNotEqual(view['proposal_sha'], digest(view['proposal']))
        self.assertEqual(view['input_sha'], digest(inputs))
        self.assertEqual(inputs, before)
