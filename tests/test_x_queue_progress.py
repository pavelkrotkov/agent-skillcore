"""Idle queue intake stays read-only and concurrent arrivals remain atomic."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from x_fixtures import Client, CollectionCase, collect, response
from x_curator.queue import enqueue
from x_curator.storage import open_store


class QueueProgressTests(CollectionCase):
    def test_unchanged_intake_never_replays_history_or_updates_rows(self):
        collect(self.db, Client([(200, response(['1', '2']))]), 'likes', delay=0)
        enqueue(self.db)
        statements = []
        self.db.set_trace_callback(statements.append)
        for _ in range(3):
            enqueue(self.db)
        self.db.set_trace_callback(None)
        self.assertFalse(any('INSERT OR IGNORE INTO jobs' in sql or sql == 'BEGIN IMMEDIATE' for sql in statements))
        collect(self.db, Client([(200, response(['2', '3']))]), 'likes', new=True, delay=0)
        enqueue(self.db)
        self.assertEqual(self.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 3)

    def test_concurrent_enqueue_commits_one_watermark_without_losing_arrivals(self):
        collect(self.db, Client([(200, response(['1']))]), 'likes', delay=0)
        enqueue(self.db)
        collect(self.db, Client([(200, response(['2', '3']))]), 'likes', new=True, delay=0)
        barrier = Barrier(2)
        def intake():
            db = open_store(self.root)
            try:
                barrier.wait(timeout=5)
                enqueue(db)
            finally:
                db.close()
        with ThreadPoolExecutor(max_workers=2) as workers:
            list(workers.map(lambda _: intake(), range(2)))
        self.assertEqual(self.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 3)
        self.assertEqual(self.db.execute('SELECT selection_rowid FROM queue_checkpoint').fetchone()[0], 3)

    def test_maintenance_rowid_rewind_reconciles_without_resetting_jobs(self):
        collect(self.db, Client([(200, response(['1']))]), 'likes', delay=0)
        with self.db:
            self.db.execute('UPDATE selections SET rowid=rowid+100')
        enqueue(self.db)
        with self.db:
            self.db.execute("UPDATE jobs SET attempts=2,state='needs_action'")
            self.db.execute('UPDATE selections SET rowid=rowid-100')
        collect(self.db, Client([(200, response(['2']))]), 'likes', new=True, delay=0)
        enqueue(self.db)
        self.assertEqual(tuple(self.db.execute("SELECT attempts,state FROM jobs WHERE id='1'").fetchone()), (2, 'needs_action'))
        self.assertEqual(self.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 2)
