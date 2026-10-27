from unittest.mock import patch

from x_fixtures import CollectionCase, Client, collect, envelope, response, tweet_entry
from x_curator.leases import claim, fail
from x_curator.queue import enqueue, outstanding
from x_curator.storage import open_store


class QueueTests(CollectionCase):
    def test_duplicate_selections_keep_provenance_and_never_reset_work(self):
        collect(self.db, Client([(200, response(["1"]))]), "likes", delay=0)
        body = envelope([{"type": "TimelineAddEntries", "entries": [tweet_entry("1")]}], "bookmarks")
        collect(self.db, Client([(200, body)]), "bookmarks", delay=0)
        enqueue(self.db)
        job = claim(self.db, Client.account)
        fail(self.db, job["token"], "source fetch timed out; retry", 0)
        enqueue(self.db)
        self.assertEqual(self.db.execute("SELECT count(*) FROM selections").fetchone()[0], 2)
        rows = outstanding(self.db)
        self.assertEqual([(r["id"], r["state"], r["attempts"]) for r in rows], [("1", "retry", 1)])

    def test_expired_lease_restarts_without_reset_and_rejects_stale_worker(self):
        collect(self.db, Client([(200, response(["1"]))]), "likes", delay=0)
        enqueue(self.db)
        with patch("x_curator.leases.time.time", return_value=100):
            first = claim(self.db, Client.account, 14400)
        self.assertEqual(first['lease_until'], 14500)
        self.db.close()
        self.db = open_store(self.root)
        with patch("x_curator.leases.time.time", return_value=3700):
            self.assertIsNone(claim(self.db, Client.account))
        with patch("x_curator.leases.time.time", return_value=14501):
            second = claim(self.db, Client.account, 10)
            with self.assertRaisesRegex(ValueError, "superseded"):
                fail(self.db, first["token"], "late result")
            fail(self.db, second["token"], "retry fetch", 0)
            third = claim(self.db, Client.account, 10)
            fail(self.db, third["token"], "budget exhausted; inspect source")
            self.assertIsNone(claim(self.db, Client.account))
        enqueue(self.db)
        self.assertEqual(outstanding(self.db)[0]["state"], "needs_action")
        self.assertEqual(self.db.execute("SELECT count(*) FROM attempts").fetchone()[0], 3)

    def test_old_and_new_sources_share_claims(self):
        collect(self.db, Client([(200, response(["1", "2", "3"]))]), "likes", delay=0)
        enqueue(self.db)
        first = claim(self.db, Client.account)
        collect(self.db, Client([(200, response(["4"]))]), "likes", new=True, delay=0)
        enqueue(self.db)
        second = claim(self.db, Client.account)
        third = claim(self.db, Client.account)
        self.assertEqual([j["id"] for j in (first, second, third)], ["1", "4", "2"])
