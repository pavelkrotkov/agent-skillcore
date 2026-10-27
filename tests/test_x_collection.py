import unittest

from x_fixtures import Client, CollectionCase, collect, open_store, response, selected_entries, sha256


class CollectionTests(CollectionCase):

    def test_fresh_pagination_preserves_bytes_deduplicates_and_reports_boundary(self):
        """Overlapping pages are normal; API exhaustion cannot prove all history."""
        first = response(["1", "2"], "next")
        client = Client([(200, first), (200, response(["2", "3"]))])
        result = collect(self.db, client, "likes", delay=0)
        self.assertEqual(client.cursors, [None, "next"])
        self.assertEqual(result["selected"], 3)
        self.assertEqual(result["state"], "timeline_end")
        self.assertFalse(result["historical_complete"])
        row = self.db.execute("SELECT body,sha256 FROM responses WHERE number=1").fetchone()
        self.assertEqual((row[0], row[1]), (first, sha256(first)))
        self.assertEqual(len(selected_entries(self.db, result["id"])), 3)

    def test_interruption_resumes_committed_cursor_and_total_budget(self):
        """A failed request counts, while its uncommitted page is fetched again."""
        client = Client([(200, response(["1"], "next")), RuntimeError("connection lost")])
        with self.assertRaises(RuntimeError):
            collect(self.db, client, "likes", delay=0)
        retry = Client([(200, response(["2"], "later"))])
        result = collect(self.db, retry, "likes", limit=3, delay=0)
        self.assertEqual(retry.cursors, ["next"])
        self.assertEqual(result["requests"], 3)
        self.assertEqual(result["state"], "collecting")
        self.assertEqual(collect(self.db, Client([]), "likes", limit=3)["selected"], 2)

    def test_account_switch_and_new_run_do_not_reuse_old_cursors(self):
        """Changing an existing authenticated account must isolate pagination."""
        collect(self.db, Client([(200, response(["1"], "next"))]), "likes", limit=1, delay=0)
        other = Client([(200, response(["2"]))])
        other.account = "other-synthetic-account"
        result = collect(self.db, other, "likes", delay=0)
        self.assertEqual(other.cursors, [None])
        self.assertEqual(result["selected"], 1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM collections").fetchone()[0], 2)


if __name__ == "__main__":
    unittest.main()
