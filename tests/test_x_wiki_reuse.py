from copy import deepcopy
import json

from x_wiki_fixtures import WikiCase
from x_curator.wiki_catalog import prepare
from x_curator.wiki_contract import validate
from x_curator.wiki_projection import merge
from x_curator.wiki_keys import page_key
from x_curator.wiki_prompts import prompt, request
from x_curator.receipts import digest


class WikiReuseTests(WikiCase):
    def test_legacy_incremental_assignment_reuses_page_and_retains_prior_claims(self):
        self.mapping['pages'][0].pop('synthesis')
        existing = dict(self.mapping['pages'][0], aliases=[], claims=[
            {'publication': 'previous-publication', 'claim': 'prior-claim'}])
        pages = {page_key(existing): deepcopy(existing)}
        inputs = prepare(self.sources, {}, [self.publication])
        inputs.pop('organization')
        inputs.pop('catalog_projection')
        inputs.pop('final_format')
        inputs.pop('publication_references')
        inputs['known_keys'] = list(pages)
        inputs['catalog'] = [dict(existing, evidence=[])]
        packet = dict(self.mapping, input_sha=digest(inputs))
        validate(packet, inputs)
        merge(pages, packet['pages'][0], packet['pages'][0]['claims'])
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[page_key(existing)]['claims'],
                         existing['claims'] + packet['pages'][0]['claims'])
        self.assertEqual(pages[page_key(existing)]['description'], existing['description'])
        for role in ('organize', 'organize_review'):
            req = request(role, inputs, packet if role == 'organize_review' else None)
            trusted, _, payload = prompt(req).partition('\nUNTRUSTED INPUTS:\n')
            self.assertIn('incremental assignments', trusted)
            self.assertIn('matching key does not establish semantic compatibility', trusted)
            self.assertEqual(json.loads(payload), dict(req, input_sha=digest(inputs),
                                                       proposal_sha=digest(req['proposal'])))
