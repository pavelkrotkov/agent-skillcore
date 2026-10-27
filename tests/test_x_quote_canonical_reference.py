from copy import deepcopy
import unittest

from test_x_currentness import source
from test_x_source_presentation import posts
from test_x_profile_citations import packet
from x_curator.evidence import validate_revision


class CanonicalReferenceTests(unittest.TestCase):
    def setUp(self):
        self.original = source()
        posts(self.original)[0]['legacy'].update(quoted_status_id_str='2', quoted_status_permalink={
            'expanded': 'https://twitter.com/old_name/status/2', 'display': 'twitter.com/old_name/status/2'})
        self.changed = deepcopy(self.original)
        posts(self.changed)[0]['legacy']['quoted_status_permalink'] = {'expanded': 'https://x.com/i/status/2'}
        self.captures = {'selection': {'kind': 'selection', 'source': {'entry': self.original}}}

    def test_cited_url_reference_does_not_relax_noncase_canonicalization(self):
        before = deepcopy(self.original)
        with self.assertRaisesRegex(ValueError, 'revision changed'):
            validate_revision(self.captures, {'entry': self.changed}, packet('https://twitter.com/old_name/status/2'))
        self.assertEqual(self.original, before)

    def test_cited_reference_allows_handle_case_only_refresh(self):
        changed = deepcopy(self.original)
        posts(changed)[0]['legacy']['quoted_status_permalink'].update(
            expanded='https://twitter.com/Old_Name/status/2', display='twitter.com/Old_Name/status/2')
        validate_revision(self.captures, {'entry': changed}, packet('https://twitter.com/old_name/status/2'))

    def test_explicit_literal_url_claim_and_display_citation_remain_strict(self):
        changed = deepcopy(self.original)
        posts(changed)[0]['legacy']['quoted_status_permalink'].update(
            expanded='https://twitter.com/Old_Name/status/2', display='twitter.com/Old_Name/status/2')
        value = packet('https://twitter.com/old_name/status/2')
        value['claims'][0]['text'] = 'The URL is https://twitter.com/old_name/status/2'
        for decision in (value, packet('twitter.com/old_name/status/2')):
            with self.subTest(decision=decision), self.assertRaisesRegex(ValueError, 'revision changed'):
                validate_revision(self.captures, {'entry': changed}, decision)

    def test_query_and_fragment_case_changes_are_not_handle_refreshes(self):
        for old_suffix, new_suffix in (('?ref=a', '?ref=A'), ('#section', '#Section')):
            original, changed = deepcopy(self.original), deepcopy(self.original)
            quote = 'https://twitter.com/old_name/status/2' + old_suffix
            posts(original)[0]['legacy']['quoted_status_permalink']['expanded'] = quote
            posts(changed)[0]['legacy']['quoted_status_permalink']['expanded'] = 'https://twitter.com/Old_Name/status/2' + new_suffix
            captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
            with self.subTest(suffix=old_suffix), self.assertRaisesRegex(ValueError, 'revision changed'):
                validate_revision(captures, {'entry': changed}, packet(quote))

    def test_changed_target_external_destination_and_noncanonical_alias_still_block(self):
        for target in ('https://x.com/i/status/3', 'https://example.org/i/status/2', 'https://x.com/new_name/status/2'):
            changed = deepcopy(self.changed)
            posts(changed)[0]['legacy']['quoted_status_permalink']['expanded'] = target
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, 'revision changed'):
                validate_revision(self.captures, {'entry': changed}, packet('https://twitter.com/old_name/status/2'))
