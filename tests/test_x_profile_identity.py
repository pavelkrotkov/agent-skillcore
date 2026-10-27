from copy import deepcopy
import unittest

from test_x_currentness import source
from test_x_source_presentation import posts
from test_x_profile_citations import packet
from x_curator.evidence import validate_revision
from x_curator.source_currentness import currentness
from x_curator.revisions import revision


class ProfileIdentityTests(unittest.TestCase):
    def test_profile_metadata_is_bound_only_when_cited(self):
        for position in (0, 1):
            original = source()
            user = posts(original)[position]['core']['user_results']['result']
            user.update(core={'name': 'Synthetic name'}, location={'location': 'Synthetic city'},
                        professional={'category': [{'id': 1, 'name': 'Synthetic role'}]},
                        unknown_profile_evidence='Synthetic evidence', is_blue_verified=True)
            changed = deepcopy(original)
            new = posts(changed)[position]['core']['user_results']['result']
            new.update(core={'name': 'Other name'}, location={'location': 'Other city'},
                       professional={'category': [{'id': 2, 'name': 'Other role'}]},
                       unknown_profile_evidence='Other evidence', is_blue_verified=False)
            captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
            with self.subTest(position=position):
                self.assertNotEqual(revision(original), revision(changed))
                validate_revision(captures, {'entry': changed}, packet('Text'))
                for quote in ('Synthetic name', 'Synthetic city', 'Synthetic role', 'Synthetic evidence'):
                    with self.assertRaisesRegex(ValueError, 'revision changed'):
                        validate_revision(captures, {'entry': changed}, packet(quote))

    def test_profile_identity_and_missing_identity_fail_closed(self):
        for identity in (None, '', 123, 'author'):
            original = source()
            user = posts(original)[0]['core']['user_results']['result']
            user['rest_id'] = identity
            changed = deepcopy(original)
            new = posts(changed)[0]['core']['user_results']['result']
            if identity == 'author':
                new['rest_id'] = 'different-author'
            else:
                new['legacy']['name'] = 'Different name'
            with self.subTest(identity=identity):
                self.assertNotEqual(currentness(original), currentness(changed))

    def test_nested_native_users_preserve_identity_and_cited_profile_evidence(self):
        original = source()
        card = posts(original)[0]['card']['legacy']
        card['user_refs_results'] = [{'result': {'__typename': 'User', 'rest_id': 'card-author',
                                               'profile_bio': {'description': 'Card biography'}}}]
        changed = deepcopy(original)
        user = posts(changed)[0]['card']['legacy']['user_refs_results'][0]['result']
        user['profile_bio']['description'] = 'Other biography'
        captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
        validate_revision(captures, {'entry': changed}, packet('Text'))
        with self.assertRaisesRegex(ValueError, 'revision changed'):
            validate_revision(captures, {'entry': changed}, packet('Card biography'))
        user['rest_id'] = 'different-card-author'
        self.assertNotEqual(currentness(original), currentness(changed))

    def test_unknown_post_evidence_remains_strict(self):
        original = source()
        posts(original)[0]['unknown_evidence'] = 'Original evidence'
        changed = deepcopy(original)
        posts(changed)[0]['unknown_evidence'] = 'Changed evidence'
        self.assertNotEqual(currentness(original), currentness(changed))

    def test_structural_identity_strings_cannot_hide_profile_citations(self):
        for quote in ('User', 'Tweet', '1', 'author', 'synthetic-encoded-id'):
            original = source()
            user = posts(original)[0]['core']['user_results']['result']
            user.update(__typename='User', id='synthetic-encoded-id', core={'name': quote})
            changed = deepcopy(original)
            posts(changed)[0]['core']['user_results']['result']['core']['name'] = 'Changed name'
            captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
            with self.subTest(quote=quote), self.assertRaisesRegex(ValueError, 'revision changed'):
                validate_revision(captures, {'entry': changed}, packet(quote))

    def test_body_citation_matching_a_type_label_remains_body_evidence(self):
        original = source()
        posts(original)[0]['legacy']['full_text'] = 'Tweet'
        user = posts(original)[0]['core']['user_results']['result']
        user.update(__typename='User', core={'name': 'Tweet'})
        changed = deepcopy(original)
        posts(changed)[0]['core']['user_results']['result']['core']['name'] = 'Other name'
        captures = {'selection': {'kind': 'selection', 'source': {'entry': original}}}
        validate_revision(captures, {'entry': changed}, packet('Tweet'))
