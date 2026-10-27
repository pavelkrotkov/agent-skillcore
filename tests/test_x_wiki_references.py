from copy import deepcopy
from unittest import TestCase

from x_wiki_final_fixtures import compact
from x_curator import wiki_catalog, wiki_final
from x_curator.receipts import digest, encoded
from x_curator.wiki_notes import request
from x_curator.wiki_prompt_payload import payload


class WikiReferenceTests(TestCase):
    def setUp(self):
        self.identity = 'a' * 64
        claims = [dict(id='c' + str(n), text='Synthetic opinion.') for n in range(40)]
        self.inputs = wiki_catalog.prepare({self.identity: dict(packet=dict(claims=claims))}, {}, [self.identity])
        self.inputs['publication_references'] = 'short/v1'
        refs = [dict(publication=self.identity, claim=c['id']) for c in claims]
        self.packet = dict(input_sha=digest(self.inputs), pages=[dict(kind='concept', title='Synthetic references',
            description='Synthetic reference round-trip.', claims=refs, related=[],
            synthesis=[dict(text='Synthetic claims exercise canonical references.', claims=refs)])])

    def test_short_model_payload_resolves_exact_canonical_validated_proposal(self):
        before = deepcopy(self.inputs)
        req = request('organize', self.inputs)
        visible = payload(dict(req, proposal=self.packet))
        alias = next(iter(visible['bundle']['wiki_inputs']['sources']))
        self.assertNotEqual(alias, self.identity)
        self.assertEqual(visible['proposal']['pages'][0]['claims'][0]['publication'], alias)
        response = dict(content=[dict(type='text', text=wiki_final.feedback(self.inputs, self.packet))])
        self.assertEqual(wiki_final.output(compact(req, visible['proposal'], response), self.inputs), self.packet)
        self.assertGreater(len(encoded(self.packet)) - len(encoded(visible['proposal'])), 4000)
        self.assertEqual(self.inputs, before)

    def test_unknown_changed_and_unmarked_references_cannot_select_wrong_packet(self):
        req = request('organize', self.inputs)
        visible = payload(dict(req, proposal=self.packet))['proposal']
        response = dict(content=[dict(type='text', text=wiki_final.feedback(self.inputs, self.packet))])
        bad = deepcopy(visible)
        bad['pages'][0]['claims'][0]['publication'] = '@unknown'
        with self.assertRaises(ValueError):
            wiki_final.output(compact(req, bad, response), self.inputs)
        changed = dict(self.inputs, sources={'b' * 64: self.inputs['sources'][self.identity]})
        with self.assertRaises(ValueError):
            wiki_final.output(compact(req, visible, response), changed)
        old = dict(self.inputs)
        old.pop('publication_references')
        packet = dict(self.packet, input_sha=digest(old))
        old_request = request('organize', old)
        self.assertEqual(payload(dict(old_request, proposal=packet))['proposal'], packet)
        self.assertEqual(wiki_final.output(compact(old_request, packet), old), packet)
