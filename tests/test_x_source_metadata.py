from copy import deepcopy
import unittest

from test_x_currentness import source
from test_x_source_presentation import posts
from test_x_profile_citations import packet
from x_curator.evidence import validate_revision
from x_curator.revisions import revision


def card(entry, mapping=False):
    bindings = posts(entry)[0]['card']['legacy']['binding_values']
    if mapping:
        bindings = {item['key']: item['value'] for item in bindings}
        posts(entry)[0]['card']['legacy']['binding_values'] = bindings
    return bindings


def preview(mapping=False):
    entry = source()
    bindings = card(entry)
    bindings[0]['value']['type'] = 'IMAGE'
    bindings.append({'key': 'thumbnail_image_alt_text',
                     'value': {'type': 'STRING', 'string_value': 'Preview'}})
    card(entry, mapping)
    return entry


def validate(original, changed, quote='Preview'):
    captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
    validate_revision(captures, {'entry': changed}, packet(quote))


def mention(entry):
    return posts(entry)[0]['note_tweet']['note_tweet_results']['result']['entity_set']['user_mentions'][0]


class SourceMetadataTests(unittest.TestCase):
    def test_duplicate_preview_rendition_can_disappear_without_losing_cited_alt(self):
        for mapping in (False, True):
            original = preview(mapping)
            changed = deepcopy(original)
            bindings = card(changed)
            bindings.pop('thumbnail_image_original' if mapping else 0)
            self.assertNotEqual(revision(original), revision(changed))
            validate(original, changed)
            validate(changed, original)

    def test_preview_semantic_changes_and_untyped_or_foreign_images_remain_strict(self):
        for field, value in (('alt', 'Changed'), ('unknown', 'Evidence'),
                             ('url', 'https://example.org/image')):
            original, changed = preview(), preview()
            card(changed)[0]['value']['image_value'][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'revision changed'):
                validate(original, changed)
        for key in ('type', 'string_value'):
            original = preview()
            card(original)[-1]['value'].pop(key)
            changed = deepcopy(original)
            card(changed).pop(0)
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'revision changed'):
                validate(original, changed)

    def test_missing_image_type_and_changed_explicit_alt_remain_strict(self):
        original = preview()
        card(original)[0]['value'].pop('type')
        changed = deepcopy(original)
        card(changed).pop(0)
        with self.assertRaisesRegex(ValueError, 'revision changed'):
            validate(original, changed)
        original, changed = preview(), preview()
        card(changed)[-1]['value']['string_value'] = 'Changed'
        with self.assertRaisesRegex(ValueError, 'revision changed'):
            validate(original, changed)

    def test_note_mentions_follow_stable_identity_and_citation_rules(self):
        original = source()
        note = posts(original)[0]['note_tweet']['note_tweet_results']['result']
        note['entity_set'] = {'user_mentions': [dict(id_str='2', name='Old name', screen_name='handle', indices=[0, 6])]}
        changed = deepcopy(original)
        mention(changed)['name'] = 'New name'
        validate(original, changed, 'Text')
        with self.assertRaisesRegex(ValueError, 'revision changed'):
            validate(original, changed, 'Old name')
        for field, value in (('id_str', '3'), ('indices', [1, 7])):
            changed = deepcopy(original)
            mention(changed)[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'revision changed'):
                validate(original, changed, 'Text')
        mention(original).pop('id_str')
        changed = deepcopy(original)
        mention(changed)['name'] = 'New name'
        with self.assertRaisesRegex(ValueError, 'revision changed'):
            validate(original, changed, 'Text')
