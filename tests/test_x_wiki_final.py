import json
from copy import deepcopy

from x_wiki_final_fixtures import compact, WikiFinalCase
from x_curator import wiki_final
from x_curator.codex_profile import execution_timeout
from x_curator.model_events import result
from x_curator.receipts import encoded
from x_curator.wiki_prompts import request


class WikiFinalTests(WikiFinalCase):
    def test_large_validated_draft_finishes_with_small_authentic_reference(self):
        log = compact(self.request, self.proposal)
        final = result(log)[1]
        self.assertGreater(len(encoded(self.proposal)), 12000)
        self.assertLess(len(encoded(final)), 160)
        self.assertEqual(execution_timeout(self.request), 120)
        self.assertEqual(wiki_final.output(log, self.inputs), self.proposal)
        old = dict(self.inputs)
        old.pop('final_format')
        self.assertNotIn('final_format', request('organize', old))
        self.assertNotIn('final_format', request('organize_review', self.inputs, self.proposal))

    def test_incomplete_missing_foreign_failed_or_changed_draft_cannot_resolve(self):
        original = json.loads(compact(self.request, self.proposal))
        def changed(mode):
            value = deepcopy(original)
            events = [json.loads(line) for line in value['events'].splitlines()]
            item = events[1]['item']
            if mode == 'incomplete': events.pop()
            if mode == 'missing': events.pop(1)
            if mode == 'foreign': item['server'] = 'elsewhere'
            if mode == 'failed': item['result']['isError'] = True
            if mode == 'changed': item['arguments']['proposal']['pages'][0]['description'] = 'Changed.'
            value['events'] = '\n'.join(encoded(event).decode() for event in events)
            return encoded(value)
        for mode in ('incomplete', 'missing', 'foreign', 'failed', 'changed'):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                wiki_final.output(changed(mode), self.inputs)

    def test_compact_reference_revalidates_draft_and_binds_exact_controller_request(self):
        invalid = deepcopy(self.proposal)
        invalid['pages'][0]['claims'] = []
        with self.assertRaises(ValueError):
            wiki_final.output(compact(self.request, invalid), self.inputs)
        changed = dict(self.inputs, catalog_sha='changed')
        with self.assertRaisesRegex(ValueError, 'controller request'):
            wiki_final.output(compact(self.request, self.proposal), changed)
