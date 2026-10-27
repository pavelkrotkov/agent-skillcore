from copy import deepcopy
from unittest import TestCase

from x_fixtures import SCRIPTS
from x_curator.receipts import digest
from x_curator.wiki_catalog import prepare
from x_curator.wiki_contract import validate
from x_curator.wiki_keys import page_key


class ZKConnectionTests(TestCase):
    def setUp(self):
        self.sources = {name: {'packet': {'claims': [{'id': 'c1', 'text': name}]}}
                        for name in ('general', 'application')}
        self.refs = {name: dict(publication=name, claim='c1') for name in self.sources}
        self.pages = [dict(kind='concept', title=name, description=name, aliases=[],
                          claims=[ref], related=[], synthesis=[dict(text=name, claims=[ref])])
                      for name, ref in self.refs.items()]
        for page, target in zip(self.pages, reversed(self.pages)):
            page['related'] = [dict(kind=target['kind'], title=target['title'],
                                   reason='The narrower application uses the general mechanism.', claims=page['claims'][:])]

    def test_one_sided_connections_fail_then_corrected_reciprocal_links_pass(self):
        inputs = prepare(self.sources, {}, list(self.sources))
        inputs['link_support'] = 'target-evidence/v1'
        packet = dict(input_sha=digest(inputs), pages=self.pages)
        with self.assertRaisesRegex(ValueError, 'target evidence'):
            validate(packet, inputs)
        for page in self.pages:
            page['claims'] = list(self.refs.values())
            page['related'][0]['claims'] = list(self.refs.values())
        validate(packet, inputs)

    def test_catalog_target_evidence_is_required_without_rewriting_the_target(self):
        source, target = self.pages
        inputs = prepare(self.sources, {page_key(target): target}, ['general'])
        inputs['link_support'] = 'target-evidence/v1'
        source['claims'].append(self.refs['application'])
        packet = dict(input_sha=digest(inputs), pages=[source])
        with self.assertRaisesRegex(ValueError, 'target evidence'):
            validate(packet, inputs)
        source['related'][0]['claims'].append(self.refs['application'])
        validate(packet, inputs)

    def test_old_inputs_keep_their_original_connection_contract(self):
        inputs = prepare(self.sources, {}, list(self.sources))
        inputs.pop('link_support', None)
        packet = dict(input_sha=digest(inputs), pages=deepcopy(self.pages))
        validate(packet, inputs)
