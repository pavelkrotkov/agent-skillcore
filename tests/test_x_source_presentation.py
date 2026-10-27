from copy import deepcopy
import unittest

from test_x_currentness import source
from x_curator.evidence import validate_revision
from x_curator.revisions import revision
from x_curator.source_currentness import currentness


def posts(entry):
    post = entry['content']['itemContent']['tweet_results']['result']
    return post, post['quoted_status_result']['result']


class PresentationTests(unittest.TestCase):
    def test_client_avatar_and_biography_offsets_preserve_receipts(self):
        original = source()
        for post in posts(original):
            post['source'] = 'Synthetic desktop client'
            user = post['core']['user_results']['result']
            user['avatar'] = {'image_url': 'https://example.org/avatar-one.jpg'}
            user['legacy']['entities'] = {'description': {'urls': [
                {'expanded_url': 'https://example.org/about', 'indices': [3, 7]}]}}
        changed = deepcopy(original)
        for post in posts(changed):
            post['source'] = 'Synthetic mobile client'
            user = post['core']['user_results']['result']
            user['avatar']['image_url'] = 'https://example.org/avatar-two.jpg'
            user['legacy']['entities']['description']['urls'][0]['indices'] = [9, 13]
        frozen = deepcopy(original)
        self.assertNotEqual(revision(original), revision(changed))
        self.assertEqual(currentness(original), currentness(changed))
        validate_revision({'selection': {'kind': 'selection', 'source': {'entry': original}}},
                          {'entry': changed}, {'claims': [{'citations': [{'capture': 'selection', 'quote': 'Researcher'}]}]})
        self.assertEqual(original, frozen)
        posts(changed)[0]['core']['user_results']['result']['legacy']['entities']['description']['urls'][0]['expanded_url'] = 'https://example.org/other'
        self.assertNotEqual(currentness(original, ('https://example.org/about',)),
                            currentness(changed, ('https://example.org/about',)))

    def test_native_preview_variants_refresh_but_external_targets_remain_strict(self):
        for name in ('thumbnail_image_small', 'summary_photo_image_x_large',
                     'photo_image_full_size', 'player_image_original', 'player_image_large'):
            original = source()
            for post in posts(original):
                post['card'] = {'legacy': {'binding_values': {name: {
                    'image_value': {'url': 'https://pbs.twimg.com/card_img/one', 'alt': 'Preview'}}}}}
            changed = deepcopy(original)
            for post in posts(changed):
                post['card']['legacy']['binding_values'][name]['image_value']['url'] = 'https://pbs.twimg.com/card_img/two'
            with self.subTest(name=name):
                self.assertNotEqual(revision(original), revision(changed))
                self.assertEqual(currentness(original), currentness(changed))
                posts(changed)[0]['card']['legacy']['binding_values'][name]['image_value']['url'] = 'https://example.org/other.jpg'
                self.assertNotEqual(currentness(original), currentness(changed))
                posts(changed)[0]['card']['legacy']['binding_values'][name]['image_value'].update(url='https://pbs.twimg.com/card_img/two', alt='Changed alt')
                self.assertNotEqual(currentness(original), currentness(changed))
