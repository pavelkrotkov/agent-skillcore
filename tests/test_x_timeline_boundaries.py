import unittest

from x_fixtures import Client, CollectionCase, collect, envelope, tweet_entry


class TimelineBoundaryTests(CollectionCase):
    def test_controls_alone_never_exhaust_but_pinned_ids_survive(self):
        cases = [({"type": "TimelineClearCache"}, 0),
                 ({"type": "TimelineTerminateTimeline", "direction": "Top"}, 0),
                 ({"type": "TimelinePinEntry", "entry": tweet_entry("1")}, 1)]
        for kind in ("likes", "bookmarks"):
            for instruction, count in cases:
                result = collect(self.db, Client([(200, envelope([instruction], kind))]), kind, new=True, delay=0)
                self.assertEqual((result["state"], result["selected"]), ("blocked", count))

    def test_partial_pages_preserve_valid_ids_without_advancing(self):
        malformed = {"entryId": "tweet-2", "content": {}}
        entries = [tweet_entry("1"), {"entryId": "unknown"}, malformed]
        for kind in ("likes", "bookmarks"):
            body = envelope([{"type": "TimelineAddEntries", "entries": entries}], kind)
            result = collect(self.db, Client([(200, body)]), kind, new=True, delay=0)
            self.assertEqual((result["state"], result["selected"]), ("blocked", 2))
            self.assertIsNone(result["cursor"])
            self.assertEqual(self.db.execute("SELECT availability FROM selections WHERE run=? AND id='2'", (result["id"],)).fetchone()[0], "malformed")

    def test_valid_bookmark_end_is_recognized(self):
        body = envelope([{"type": "TimelineAddEntries", "entries": [tweet_entry("1")]},
                         {"type": "TimelineTerminateTimeline", "direction": "Bottom"}], "bookmarks")
        result = collect(self.db, Client([(200, body)]), "bookmarks", delay=0)
        self.assertEqual((result["state"], result["selected"]), ("timeline_end", 1))

    def test_null_bottom_cursor_blocks_without_losing_selection(self):
        entries = [tweet_entry("1"), {"entryId": "cursor-bottom-1", "content": {"value": None}}]
        for kind in ("likes", "bookmarks"):
            body = envelope([{"type": "TimelineAddEntries", "entries": entries}], kind)
            result = collect(self.db, Client([(200, body)]), kind, new=True, delay=0)
            self.assertEqual((result["state"], result["selected"]), ("blocked", 1))

    def test_visibility_wrappers_preserve_accessible_tweets(self):
        entry = tweet_entry("1")
        entry["content"]["itemContent"]["tweet_results"]["result"] = {
            "__typename": "TweetWithVisibilityResults", "tweet": {"rest_id": "1", "legacy": {"full_text": "Synthetic"}}}
        body = envelope([{"type": "TimelineAddEntries", "entries": [entry]}])
        result = collect(self.db, Client([(200, body)]), "likes", delay=0)
        self.assertEqual((result["state"], result["selected"], result["unavailable"]), ("timeline_end", 1, 0))
        self.assertEqual(self.db.execute("SELECT availability FROM selections").fetchone()[0], "available")

    def test_retry_repairs_malformed_selection_and_retains_both_responses(self):
        malformed = {"entryId": "tweet-2", "content": {}}
        first = envelope([{"type": "TimelineAddEntries", "entries": [malformed]}])
        second = envelope([{"type": "TimelineAddEntries", "entries": [tweet_entry("2")]}])
        collect(self.db, Client([(200, first)]), "likes", delay=0)
        result = collect(self.db, Client([(200, second)]), "likes", delay=0)
        row = self.db.execute("SELECT availability,response,entry FROM selections").fetchone()
        self.assertEqual((result["state"], row[0], row[1]), ("timeline_end", "available", 2))
        self.assertIn('"rest_id": "2"', row[2])
        self.assertEqual([r[0] for r in self.db.execute("SELECT body FROM responses ORDER BY number")], [first, second])


if __name__ == "__main__":
    unittest.main()
