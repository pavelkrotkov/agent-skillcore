from copy import deepcopy
from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator.wiki_contract import validate
from x_curator.wiki_mapping import map_sources
from x_curator.wiki_keys import page_key


class WikiContractTests(WikiCase):
    def test_unknown_omitted_and_duplicate_claims_are_rejected(self):
        for refs in ([], [{'publication': self.publication, 'claim': 'missing'}], self.mapping['pages'][0]['claims'] * 2):
            packet = deepcopy(self.mapping)
            packet['pages'][0]['claims'] = refs
            with self.assertRaises(ValueError):
                validate(packet, self.inputs)

    def test_relationship_needs_real_target_and_support(self):
        packet = deepcopy(self.mapping)
        packet['pages'][0]['related'] = [{'kind': 'entity', 'title': 'Missing target', 'reason': 'Related example.', 'claims': []}]
        with self.assertRaises(ValueError):
            validate(packet, self.inputs)

    def test_failed_mapping_attempts_are_durable_and_bounded(self):
        with patch('x_curator.wiki_mapping.runner', side_effect=RuntimeError('synthetic outage')) as call:
            for _ in range(3):
                with self.assertRaisesRegex(RuntimeError, 'outage'):
                    map_sources(self.db, self.inputs)
            with self.assertRaisesRegex(ValueError, 'budget exhausted'):
                map_sources(self.db, self.inputs)
        self.assertEqual(call.call_count, 3)
        self.assertEqual(self.db.execute('SELECT attempts FROM wiki_sources').fetchone()[0], 3)

    def test_unseen_existing_meaning_cannot_be_silently_merged(self):
        self.inputs['known_keys'] = [page_key(self.mapping['pages'][0])]
        from x_curator.receipts import digest
        self.mapping['input_sha'] = digest(self.inputs)
        with self.assertRaisesRegex(ValueError, 'meaning was absent'):
            validate(self.mapping, self.inputs)
