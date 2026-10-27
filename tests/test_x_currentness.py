from copy import deepcopy
import unittest

from x_fixtures import tweet_entry
from x_curator.evidence import validate_revision
from x_curator.revisions import revision
from x_curator.source_currentness import currentness


def source():
    entry = tweet_entry('1')
    tweet = entry['content']['itemContent']['tweet_results']['result']
    tweet.update(legacy={'full_text': 'Text', 'source': 'Web', 'in_reply_to_status_id_str': '3',
                         'entities': {'urls': [{'expanded_url': 'https://example.org/a'}]},
                         'extended_entities': {'media': [{'media_url_https': 'https://example.org/a.jpg', 'ext_alt_text': 'Chart'}]}},
                 core={'user_results': {'result': {'rest_id': 'author', 'legacy': {
                     'name': 'Author', 'description': 'Researcher', 'profile_banner_url': 'banner-one'},
                     'profile_bio': {'description': 'Researcher'}}}},
                 note_tweet={'note_tweet_results': {'result': {'text': 'Long text'}}},
                 quoted_status_result={'result': {'legacy': {'full_text': 'Quote'},
                     'core': {'user_results': {'result': {'rest_id': 'quoted-author',
                         'legacy': {'description': 'Quoted biography'},
                         'profile_bio': {'description': 'Quoted biography'}}}}}},
                 card={'legacy': {'binding_values': [
                     {'key': 'thumbnail_image_original', 'value': {'image_value': {'url': 'https://pbs.twimg.com/card_img/one', 'alt': 'Preview'}}},
                     {'key': 'title', 'value': {'string_value': 'Headline'}},
                     {'key': 'description', 'value': {'string_value': 'Summary'}},
                     {'key': 'card_url', 'value': {'string_value': 'https://example.org/article'}}]}})
    return entry


class CurrentnessTests(unittest.TestCase):
    def test_presentation_drift_does_not_rebind_immutable_revision(self):
        original, changed = source(), source()
        post = changed['content']['itemContent']['tweet_results']['result']
        post['legacy']['source'] = 'Mobile'
        post['core']['user_results']['result']['legacy']['profile_banner_url'] = 'banner-two'
        post['card']['legacy']['binding_values'][0]['value']['image_value']['url'] = 'https://pbs.twimg.com/card_img/two'
        self.assertNotEqual(revision(original), revision(changed))
        self.assertEqual(currentness(original), currentness(changed))
        self.assertEqual(currentness(original)[0], 'source-currentness/v8')
        self.assertEqual(original, source())

    def test_uncited_biographies_refresh_but_cited_biographies_block(self):
        original, changed = source(), source()
        post = changed['content']['itemContent']['tweet_results']['result']
        focal = post['core']['user_results']['result']
        quoted = post['quoted_status_result']['result']['core']['user_results']['result']
        for profile in (focal, quoted):
            profile['legacy']['description'] = 'Updated biography'
            profile['profile_bio']['description'] = 'Updated biography'
        self.assertNotEqual(revision(original), revision(changed))
        self.assertEqual(currentness(original), currentness(changed))
        captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
        validate_revision(captures, {'entry': changed})
        validate_revision(captures, {'entry': changed}, {'claims': [{'citations': [{'capture': 'selection', 'quote': 'Text'}]}]})
        for quote in ('Researcher', 'Quoted biography'):
            with self.subTest(quote=quote), self.assertRaisesRegex(ValueError, 'revision changed'):
                validate_revision(captures, {'entry': changed}, {'claims': [{'citations': [{'capture': 'selection', 'quote': quote}]}]})
        self.assertEqual(original, source())
        absent = source()
        absent['content']['itemContent']['tweet_results']['result']['core']['user_results']['result'].pop('profile_bio')
        refreshed = deepcopy(absent)
        refreshed['content']['itemContent']['tweet_results']['result']['core']['user_results']['result']['profile_bio'] = {'description': 'New bio'}
        validate_revision({'selection': {'kind': 'selection', 'source': {'entry': absent}}}, {'entry': refreshed})

    def test_profile_language_refresh_does_not_change_source_evidence(self):
        original = source()
        captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
        for quoted in (False, True):
            for language in ('en', 'fr', None):
                changed = deepcopy(original)
                post = changed['content']['itemContent']['tweet_results']['result']
                post = post['quoted_status_result']['result'] if quoted else post
                post['core']['user_results']['result']['profile_description_language'] = language
                with self.subTest(quoted=quoted, language=language):
                    self.assertNotEqual(revision(original), revision(changed))
                    validate_revision(captures, {'entry': changed})
                    validate_revision(captures, {'entry': changed},
                                      {'claims': [{'citations': [{'capture': 'selection', 'quote': 'Researcher'}]}]})
                    reverse = {'selection': {'kind': 'selection', 'source': {'entry': changed}}}
                    validate_revision(reverse, {'entry': original})
        self.assertEqual(original, source())

    def test_body_citation_does_not_bind_incidental_biography_word(self):
        original = source()
        old = original['content']['itemContent']['tweet_results']['result']['core']['user_results']['result']
        old['legacy']['description'] = 'Researcher illustrating Text examples'
        old['profile_bio']['description'] = 'Researcher illustrating Text examples'
        changed = deepcopy(original)
        new = changed['content']['itemContent']['tweet_results']['result']['core']['user_results']['result']
        new['legacy']['description'] = 'Updated Text biography'
        new['profile_bio']['description'] = 'Updated Text biography'
        captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
        validate_revision(captures, {'entry': changed}, {'claims': [{'citations': [{'capture': 'selection', 'quote': 'Text'}]}]})

    def test_content_identity_context_media_and_citation_text_remain_strict(self):
        original = source()
        paths = [
            (('legacy', 'full_text'), 'Edited'), (('note_tweet', 'note_tweet_results', 'result', 'text'), 'Edited'),
            (('rest_id',), '2'), (('core', 'user_results', 'result', 'rest_id'), 'other-author'),
            (('legacy', 'in_reply_to_status_id_str'), '4'),
            (('legacy', 'entities', 'urls', 0, 'expanded_url'), 'https://example.org/b'),
            (('legacy', 'extended_entities', 'media', 0, 'media_url_https'), 'https://example.org/b.jpg'),
            (('legacy', 'extended_entities', 'media', 0, 'ext_alt_text'), 'Other alt'),
            (('quoted_status_result', 'result', 'legacy', 'full_text'), 'Other quote'),
            (('card', 'legacy', 'binding_values', 0, 'value', 'image_value', 'alt'), 'Other preview alt'),
            (('card', 'legacy', 'binding_values', 1, 'value', 'string_value'), 'Other title'),
            (('card', 'legacy', 'binding_values', 2, 'value', 'string_value'), 'Other summary'),
            (('card', 'legacy', 'binding_values', 3, 'value', 'string_value'), 'https://example.org/other')]
        for path, replacement in paths:
            changed = deepcopy(original)
            target = changed['content']['itemContent']['tweet_results']['result']
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = replacement
            with self.subTest(path=path):
                self.assertNotEqual(currentness(original), currentness(changed))
        wrapped = deepcopy(original)
        post = wrapped['content']['itemContent']['tweet_results']['result']
        wrapped['content']['itemContent']['tweet_results']['result'] = {'__typename': 'TweetWithVisibilityResults', 'tweet': post, 'limited_actions': ['Reply']}
        changed = deepcopy(wrapped)
        changed['content']['itemContent']['tweet_results']['result']['limited_actions'] = []
        self.assertNotEqual(currentness(wrapped), currentness(changed))
