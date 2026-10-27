from copy import deepcopy
import unittest

from test_x_currentness import source
from test_x_source_presentation import posts
from x_curator.evidence import validate_revision


def packet(quote):
    return {'claims': [{'citations': [{'capture': 'selection', 'quote': quote}]}]}


def set_links(post, target):
    profile = post['core']['user_results']['result']['legacy']
    profile['url'] = 'https://t.co/synthetic-old'
    profile['entities'] = {name: {'urls': [{'expanded_url': target,
        'url': 'https://t.co/synthetic-old', 'display_url': 'example.org', 'indices': [0, 4]}]}
        for name in ('description', 'url')}


class ProfileCitationTests(unittest.TestCase):
    def test_uncited_profile_links_refresh_but_cited_targets_remain_bound(self):
        for position in (0, 1):
            original = source()
            set_links(posts(original)[position], 'https://example.org/about')
            changed = deepcopy(original)
            set_links(posts(changed)[position], 'https://example.org/other')
            captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
            with self.subTest(position=position):
                validate_revision(captures, {'entry': changed})
                validate_revision(captures, {'entry': changed}, packet('Text'))
                for quote in ('https://example.org/about', 'https://t.co/synthetic-old'):
                    with self.assertRaisesRegex(ValueError, 'revision changed'):
                        validate_revision(captures, {'entry': changed}, packet(quote))

    def test_profile_website_addition_does_not_bind_body_citations(self):
        original = source()
        changed = deepcopy(original)
        set_links(posts(changed)[1], 'https://example.org/added')
        captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
        validate_revision(captures, {'entry': changed}, packet('Text'))

    def test_profile_alias_refresh_keeps_cited_expanded_destination(self):
        original = source()
        set_links(posts(original)[1], 'https://example.org/about')
        changed = deepcopy(original)
        profile = posts(changed)[1]['core']['user_results']['result']['legacy']
        profile['url'] = 'https://t.co/synthetic-new'
        for entity in profile['entities'].values():
            entity['urls'][0].update(url='https://t.co/synthetic-new', display_url='example.org/about', indices=[5, 9])
        captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
        validate_revision(captures, {'entry': changed}, packet('https://example.org/about'))

    def test_cited_display_alias_cannot_hide_destination_changes(self):
        original = source()
        set_links(posts(original)[1], 'https://example.org/about')
        profile = posts(original)[1]['core']['user_results']['result']['legacy']
        for entity in profile['entities'].values():
            entity['urls'][0]['display_url'] = 'example.org/…'
        changed = deepcopy(original)
        set_links(posts(changed)[1], 'https://example.org/other')
        captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
        with self.assertRaisesRegex(ValueError, 'revision changed'):
            validate_revision(captures, {'entry': changed}, packet('example.org/…'))

    def test_unknown_entity_and_url_fields_remain_strict(self):
        for field in ('description', 'url'):
            for nested in (False, True):
                original = source()
                set_links(posts(original)[1], 'https://example.org/about')
                entity = posts(original)[1]['core']['user_results']['result']['legacy']['entities'][field]
                (entity['urls'][0] if nested else entity)['unknown_evidence'] = 'Original evidence'
                changed = deepcopy(original)
                entity = posts(changed)[1]['core']['user_results']['result']['legacy']['entities'][field]
                (entity['urls'][0] if nested else entity)['unknown_evidence'] = 'Changed evidence'
                captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
                with self.subTest(field=field, nested=nested), self.assertRaisesRegex(ValueError, 'revision changed'):
                    validate_revision(captures, {'entry': changed}, packet('Original evidence'))

    def test_cited_legacy_biography_keeps_links_with_a_distinct_bio_mirror(self):
        original = source()
        set_links(posts(original)[1], 'https://example.org/about')
        user = posts(original)[1]['core']['user_results']['result']
        user['legacy']['description'] = 'Visit https://t.co/synthetic-old'
        user['profile_bio']['description'] = 'Separate biography'
        changed = deepcopy(original)
        set_links(posts(changed)[1], 'https://example.org/other')
        captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
        with self.assertRaisesRegex(ValueError, 'revision changed'):
            validate_revision(captures, {'entry': changed}, packet('Visit https://t.co/synthetic-old'))

    def test_external_citation_cannot_bind_incidental_profile_phrase(self):
        original = source()
        changed = deepcopy(original)
        for post in posts(changed):
            user = post['core']['user_results']['result']
            user['legacy']['description'] = 'Updated biography'
            user['profile_bio']['description'] = 'Updated biography'
        captures = {'selection': {'kind': 'selection', 'source': {'entry': original}},
                    'external': {'kind': 'http', 'text': 'Researcher'}}
        publication = packet('Researcher')
        publication['claims'][0]['citations'][0]['capture'] = 'external'
        validate_revision(captures, {'entry': changed}, publication)
        with self.assertRaisesRegex(ValueError, 'revision changed'):
            validate_revision(captures, {'entry': changed}, packet('Researcher'))
