from x_fixtures import CollectionCase, Client, collect, envelope, tweet_entry


class WrappedEntryTests(CollectionCase):
    def test_explicit_inner_types_override_visibility_wrapper(self):
        cases = [("TweetTombstone", "unavailable", "timeline_end"),
                 ("Unknown", "malformed", "blocked")]
        for kind, availability, state in cases:
            entry = tweet_entry("1")
            entry["content"]["itemContent"]["tweet_results"]["result"] = {
                "__typename": "TweetWithVisibilityResults", "tweet": {"__typename": kind}}
            body = envelope([{"type": "TimelineAddEntries", "entries": [entry]}])
            result = collect(self.db, Client([(200, body)]), "likes", new=True, delay=0)
            row = self.db.execute("SELECT availability FROM selections WHERE run=?", (result["id"],)).fetchone()
            self.assertEqual((result["state"], row[0]), (state, availability))
