import json
from copy import deepcopy
from unittest import TestCase

from x_fixtures import SCRIPTS
from x_trace_fixtures import proof
from x_curator.model_trace import verify_request
from x_curator.receipts import digest
from x_curator.wiki_prompts import prompt, request


class CompactBindingTests(TestCase):
    def test_hidden_guard_metadata_remains_bound_to_the_authentic_model_receipt(self):
        inputs = dict(catalog_projection=2, known_keys=['existing'], retired_keys=['retired'],
                      catalog_sha='catalog', publications_sha='sources', sources={}, catalog=[])
        original = request('organize', inputs)
        shown = json.loads(prompt(original).partition('\nUNTRUSTED INPUTS:\n')[2])
        self.assertNotIn('known_keys', shown['bundle']['wiki_inputs'])
        self.assertEqual(shown['input_sha'], digest(inputs))
        log = proof(original, {'synthetic': True})
        verify_request(log, original)
        for field in ('known_keys', 'retired_keys', 'catalog_sha', 'publications_sha'):
            tampered = deepcopy(original)
            tampered['bundle']['wiki_inputs'][field] = 'changed'
            with self.assertRaisesRegex(ValueError, 'input proof'):
                verify_request(log, tampered)

    def test_historical_unprojected_requests_show_the_original_guard_metadata(self):
        inputs = dict(known_keys=['existing'], sources={}, catalog=[])
        original = request('organize_review', inputs)
        shown = json.loads(prompt(original).partition('\nUNTRUSTED INPUTS:\n')[2])
        self.assertEqual(shown['bundle']['wiki_inputs'], inputs)
        verify_request(proof(original, {'synthetic': True}), original)
