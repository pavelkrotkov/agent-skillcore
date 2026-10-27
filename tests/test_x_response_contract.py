import unittest

from x_fixtures import Client, CollectionCase, collect, open_store, response, selected_entries, sha256


class CollectionTests(CollectionCase):

    def test_graphql_errors_bad_shapes_and_rate_limits_never_exhaust(self):
        """HTTP 200 error payloads are not empty timelines."""
        for status, body in [(200, b'{}'), (200, b'{"errors":[{"message":"no"}]}'), (429, b'limited')]:
            with self.subTest(status=status, body=body):
                result = collect(self.db, Client([(status, body)]), "likes", new=True, delay=0)
                self.assertEqual(result["state"], "blocked")
                self.assertEqual(result["requests"], 1)

    def test_cursor_loop_is_visible_and_does_not_drop_new_items(self):
        client = Client([(200, response(["1"], "next")), (200, response(["2"], "next"))])
        result = collect(self.db, client, "likes", delay=0)
        self.assertEqual(result["reason"], "pagination cursor loop")
        self.assertEqual(result["selected"], 2)

    def test_unavailable_selected_id_is_kept(self):
        body = response(["1"]).replace(b'"__typename": "Tweet"', b'"__typename": "TweetUnavailable"')
        result = collect(self.db, Client([(200, body)]), "likes", delay=0)
        self.assertEqual(result["selected"], 1)
        self.assertEqual(result["unavailable"], 1)

    def test_private_corpus_inside_checkout_is_rejected(self):
        (self.root / ".git").mkdir()
        with self.assertRaisesRegex(ValueError, "outside every Git"):
            open_store(self.root / "private")


if __name__ == "__main__":
    unittest.main()
