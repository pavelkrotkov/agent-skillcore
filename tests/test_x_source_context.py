from copy import deepcopy
import unittest

from test_x_currentness import source
from test_x_source_presentation import posts
from test_x_profile_citations import packet
from x_curator.evidence import validate_revision
from x_curator.source_currentness import currentness
from x_curator.revisions import revision


class SourceContextTests(unittest.TestCase):
    def test_mention_alias_refresh_keeps_identity_and_cited_alias_strict(self):
        original = source()
        posts(original)[0]['legacy']['entities']['user_mentions'] = [
            {'id_str': '2', 'id': 2, 'name': 'Synthetic author', 'screen_name': 'old_handle'}]
        changed = deepcopy(original)
        mention = posts(changed)[0]['legacy']['entities']['user_mentions'][0]
        mention.update(name='New author', screen_name='new_handle')
        captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
        self.assertNotEqual(revision(original), revision(changed))
        validate_revision(captures, {'entry': changed}, packet('Text'))
        with self.assertRaisesRegex(ValueError, 'revision changed'):
            validate_revision(captures, {'entry': changed}, packet('old_handle'))
        mention['id_str'] = '3'
        self.assertNotEqual(currentness(original), currentness(changed))

    def test_place_map_outline_is_metadata_but_post_geotags_and_region_identity_are_strict(self):
        original = source()
        legacy = posts(original)[1]['legacy']
        legacy.update(place={'id': 'synthetic-city', 'full_name': 'Synthetic city',
                             'bounding_box': {'type': 'Polygon', 'coordinates': [[], []]}},
                      geo={'type': 'Point', 'coordinates': [1.2, 3.4]})
        changed = deepcopy(original)
        latest = posts(changed)[1]['legacy']
        latest['place']['bounding_box']['coordinates'] = [[[1.0, 2.0], [3.0, 4.0]]]
        self.assertNotEqual(revision(original), revision(changed))
        self.assertEqual(currentness(original), currentness(changed))
        for field, value in (('id', 'different-city'), ('full_name', 'Different city')):
            latest['place'][field] = value
            self.assertNotEqual(currentness(original), currentness(changed))
            latest['place'][field] = legacy['place'][field]
        latest['geo']['coordinates'] = [5.6, 7.8]
        self.assertNotEqual(currentness(original), currentness(changed))
        latest['geo'] = deepcopy(legacy['geo'])
        latest['place']['bounding_box']['unknown'] = 'New evidence'
        self.assertNotEqual(currentness(original), currentness(changed))

    def test_mention_identity_string_cannot_hide_cited_alias_change(self):
        original = source()
        posts(original)[0]['legacy']['entities']['user_mentions'] = [
            {'id_str': '2', 'id': 2, 'name': '2', 'screen_name': 'old_handle'}]
        changed = deepcopy(original)
        posts(changed)[0]['legacy']['entities']['user_mentions'][0]['name'] = 'Changed name'
        captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
        with self.assertRaisesRegex(ValueError, 'revision changed'):
            validate_revision(captures, {'entry': changed}, packet('2'))
