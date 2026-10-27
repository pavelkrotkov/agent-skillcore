from copy import deepcopy
import unittest

from test_x_currentness import source
from test_x_source_presentation import posts
from test_x_profile_citations import packet
from x_curator.evidence import validate_revision
from x_curator.source_currentness import currentness
from x_curator.revisions import revision


class SourceLinksTests(unittest.TestCase):
    def test_quote_handle_alias_refresh_preserves_target_and_explicit_citations(self):
        original = source()
        legacy = posts(original)[0]['legacy']
        legacy.update(quoted_status_id_str='2', quoted_status_permalink={
            'expanded': 'https://twitter.com/old_name/status/2',
            'display': 'twitter.com/old_name/status/2', 'url': 'https://t.co/synthetic'})
        changed = deepcopy(original)
        link = posts(changed)[0]['legacy']['quoted_status_permalink']
        link.update(expanded='https://x.com/new_name/status/2', display='x.com/new_name/status/2')
        captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
        self.assertNotEqual(revision(original), revision(changed))
        validate_revision(captures, {'entry': changed}, packet('Text'))
        with self.assertRaisesRegex(ValueError, 'revision changed'):
            validate_revision(captures, {'entry': changed}, packet('https://twitter.com/old_name/status/2'))
        for target in ('https://x.com/new_name/status/3', 'https://example.org/new_name/status/2',
                       'ftp://x.com/new_name/status/2', 'https://x.com:8443/new_name/status/2'):
            link['expanded'] = target
            self.assertNotEqual(currentness(original), currentness(changed))


    def test_canonical_quote_link_alias_citations_remain_strict(self):
        original = source()
        posts(original)[0]['legacy'].update(quoted_status_id_str='2', quoted_status_permalink={
            'expanded': 'https://x.com/i/status/2', 'display': 'x.com/i/status/2'})
        changed = deepcopy(original)
        posts(changed)[0]['legacy']['quoted_status_permalink'].update(
            expanded='https://x.com/new_name/status/2', display='x.com/new_name/status/2')
        captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
        for quote in ('https://x.com/i/status/2', 'x.com/i/status/2'):
            with self.subTest(quote=quote), self.assertRaisesRegex(ValueError, 'revision changed'):
                validate_revision(captures, {'entry': changed}, packet(quote))
