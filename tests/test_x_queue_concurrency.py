from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from x_fixtures import Client, CollectionCase, collect, response
from x_curator.leases import claim, fail
from x_curator.queue import enqueue
from x_curator.storage import open_store


class QueueConcurrencyTests(CollectionCase):
    def test_simultaneous_connections_cannot_claim_same_item(self):
        collect(self.db, Client([(200, response(["1"]))]), "likes", delay=0)
        enqueue(self.db)
        barrier = Barrier(2)

        def worker():
            db = open_store(self.root)
            try:
                barrier.wait(timeout=5)
                return claim(db, Client.account)
            finally:
                db.close()

        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(lambda _: worker(), range(2)))
        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM attempts").fetchone()[0], 1)

    def test_time_is_checked_after_transaction_lock_is_acquired(self):
        collect(self.db, Client([(200, response(["1"]))]), "likes", delay=0)
        enqueue(self.db)
        clock = [100]

        def lock_acquired(sql):
            if sql == "BEGIN IMMEDIATE":
                clock[0] += 20

        self.db.set_trace_callback(lock_acquired)
        with patch("x_curator.leases.time.time", side_effect=lambda: clock[0]):
            job = claim(self.db, Client.account, 10)
            self.assertEqual(job["lease_until"], 130)
            with self.assertRaisesRegex(ValueError, "expired"):
                fail(self.db, job["token"], "result arrived after contention")
        self.db.set_trace_callback(None)
        self.assertEqual(self.db.execute("SELECT state FROM attempts").fetchone()[0], "leased")
