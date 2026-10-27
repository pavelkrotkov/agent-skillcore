from copy import deepcopy

from x_wiki_fixtures import WikiCase
from x_curator.receipts import digest
from x_curator.wiki_catalog import prepare
from x_curator.wiki_contract import validate
from x_curator.wiki_keys import page_key


class ZKContractTests(WikiCase):
    def test_synthesis_requires_approved_support_and_cannot_drop_old_evidence(self):
        page = dict(self.mapping['pages'][0], aliases=[])
        self.inputs = prepare(self.sources, {page_key(page): page}, [self.publication])
        packet = dict(self.mapping, input_sha=digest(self.inputs))
        validate(packet, self.inputs)
        for block in ([], [{'text': 'Unverified answer.', 'claims': []}]):
            broken = deepcopy(packet)
            broken['pages'][0]['synthesis'] = block
            with self.assertRaises(ValueError):
                validate(broken, self.inputs)
        self.inputs['catalog'][0]['complete'] = False
        packet['input_sha'] = digest(self.inputs)
        with self.assertRaisesRegex(ValueError, 'complete reviewed evidence'):
            validate(packet, self.inputs)

    def test_duplicate_and_retired_consolidations_are_rejected(self):
        old = dict(self.mapping['pages'][0], aliases=[])
        self.inputs = prepare(self.sources, {page_key(old): old}, [self.publication])
        new = dict(old, title='Reusable concept', replaces=[old])
        packet = dict(input_sha=digest(self.inputs), pages=[new])
        validate(packet, self.inputs)
        packet['pages'].append(dict(new, title='Second destination'))
        with self.assertRaisesRegex(ValueError, 'conflicting consolidations'):
            validate(packet, self.inputs)
        self.inputs['retired_keys'] = [page_key(new)]
        packet.update(input_sha=digest(self.inputs), pages=[new])
        with self.assertRaisesRegex(ValueError, 'retired note identities'):
            validate(packet, self.inputs)
