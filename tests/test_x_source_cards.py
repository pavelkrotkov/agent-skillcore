from copy import deepcopy
import unittest

from test_x_currentness import source
from test_x_source_presentation import posts
from test_x_profile_citations import packet
from x_curator.evidence import validate_revision
from x_curator.source_currentness import currentness
from x_curator.revisions import revision


class SourceCardTests(unittest.TestCase):

    def test_live_app_metrics_are_strict_only_when_used_as_selection_evidence(self):
        for name in ('app_star_rating', 'app_num_ratings'):
            original = source()
            posts(original)[0]['card']['legacy']['binding_values'].append(
                {'key': name, 'value': {'string_value': '4.54016', 'type': 'STRING', 'unknown': 'Original'}})
            changed = deepcopy(original)
            value = posts(changed)[0]['card']['legacy']['binding_values'][-1]['value']
            value['string_value'] = '4.54028'
            captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
            with self.subTest(name=name):
                self.assertNotEqual(revision(original), revision(changed))
                validate_revision(captures, {'entry': changed}, packet('Text'))
                with self.assertRaisesRegex(ValueError, 'revision changed'):
                    validate_revision(captures, {'entry': changed}, packet('4.54016'))
                value['unknown'] = 'Changed'
                self.assertNotEqual(currentness(original), currentness(changed))

    def test_new_native_preview_layout_does_not_change_card_evidence(self):
        original = source()
        original_card = posts(original)[0]['card']['legacy']['binding_values']
        original_card.pop(0)
        changed = deepcopy(original)
        bindings = posts(changed)[0]['card']['legacy']['binding_values']
        bindings.extend([
            {'key': 'thumbnail_image', 'value': {'type': 'IMAGE', 'image_value': {
                'url': 'https://pbs.twimg.com/card_img/synthetic', 'width': 200, 'height': 100}}},
            {'key': 'thumbnail_image_color', 'value': {'type': 'IMAGE_COLOR', 'image_color_value': {
                'palette': [{'percentage': 94.35, 'rgb': {'red': 255, 'green': 255, 'blue': 255}}]}}}])
        self.assertNotEqual(revision(original), revision(changed))
        self.assertEqual(currentness(original), currentness(changed))
        bindings[-2]['value']['image_value']['alt'] = 'New substantive alt'
        self.assertNotEqual(currentness(original), currentness(changed))
        bindings[-2]['value']['image_value'].pop('alt')
        bindings[-1]['value']['image_color_value']['palette'][0]['unknown'] = 'New evidence'
        self.assertNotEqual(currentness(original), currentness(changed))

    def test_unknown_empty_binding_presence_remains_strict(self):
        for mapping in (False, True):
            original = source()
            if mapping:
                posts(original)[0]['card']['legacy']['binding_values'] = {'title': {'string_value': 'Headline'}}
            changed = deepcopy(original)
            values = posts(changed)[0]['card']['legacy']['binding_values']
            if mapping:
                values['unknown_evidence'] = {}
            else:
                values.append({'key': 'unknown_evidence', 'value': {}})
            with self.subTest(mapping=mapping):
                self.assertNotEqual(currentness(original), currentness(changed))
