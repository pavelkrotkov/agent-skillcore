from unittest.mock import Mock

from x_fixtures import Client
from x_publication_fixtures import PublicationCase
from x_derived_fixtures import CHILD, IMAGE, ROOT, details, fetch, response
from x_curator.acquire import acquire_urls
from x_curator.evidence import bundle, capture_selection
from x_curator.leases import claim, fail_owned
from x_curator.reuse import captures


class DerivedPostTests(PublicationCase):
    def test_visible_typed_post_keeps_real_response_provenance_without_another_request(self):
        fetcher = Mock(side_effect=fetch)
        acquire_urls(self.db, self.token, {ROOT}, fetcher)
        actual = details(bundle(self.db, self.token))
        parent, original = actual[ROOT]
        _, child = actual[CHILD]
        fetcher.assert_called_once_with(ROOT)
        self.assertEqual(child['derived_from'], parent)
        self.assertEqual(child['final_url'], ROOT)
        self.assertEqual(child['focal_id'], '2')
        self.assertEqual(child['body_sha'], original['body_sha'])
        self.assertEqual(child['fetched'], original['fetched'])
        self.assertIn('Complete synthetic long post.', child['text'])
        self.assertNotIn('This is a user', child['text'])
        self.assertEqual(child['thread_scope'], ['a', '1'])
        receipt = self.db.execute('SELECT url,body_sha FROM retrievals WHERE id=?', (child['derivation_retrieval'],)).fetchone()
        self.assertEqual(tuple(receipt), (ROOT, child['body_sha']))

    def test_restart_rederives_child_from_current_parent_without_network(self):
        fetcher = Mock(side_effect=fetch)
        acquire_urls(self.db, self.token, {ROOT}, fetcher)
        old = details(bundle(self.db, self.token))
        fail_owned(self.db, self.token, 'research retry', 0)
        token = claim(self.db, Client.account)['token']
        capture_selection(self.db, token)
        self.assertEqual(set(captures(self.db, token)), {ROOT})
        acquire_urls(self.db, token, {ROOT}, fetcher)
        current = details(bundle(self.db, token))
        self.assertEqual(current[CHILD][1]['derived_from'], current[ROOT][0])
        self.assertNotEqual(current[ROOT][0], old[ROOT][0])
        self.assertEqual(current[CHILD][1]['fetched'], old[CHILD][1]['fetched'])
        fetcher.assert_called_once()

    def test_unfetched_child_media_still_blocks_the_source(self):
        fetcher = Mock(side_effect=[(200, 'application/json', response(media=True), None),
                                   (404, 'text/plain', b'Unavailable media', None)])
        with self.assertRaisesRegex(ValueError, 'HTTP 404'):
            acquire_urls(self.db, self.token, {ROOT}, fetcher)
        self.assertEqual([call.args[0] for call in fetcher.call_args_list], [ROOT, IMAGE])
        self.assertIn(CHILD, details(bundle(self.db, self.token)))
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
