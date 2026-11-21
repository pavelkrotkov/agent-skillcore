"""A concurrent retry cannot be frozen into a completed review batch."""
from x_fixtures import Client, CollectionCase, collect, response
from x_curator import batch_store, review_store
from x_curator.storage import open_store


class BatchClosingTests(CollectionCase):

    def test_closing_batch_rechecks_members_after_another_writer_changes_them(self):
        collect(self.db, Client([(200, response(['1']))]), 'likes', delay=0)
        review_store.initialize(self.db)
        with self.db:
            self.db.execute("UPDATE jobs SET state='awaiting_review'")
            self.db.execute("INSERT INTO curation_batches VALUES ('batch',?,'backlog',0,0,'open')", (Client.account,))
            self.db.execute("INSERT INTO curation_members VALUES ('batch',?,'1')", (Client.account,))
        other = open_store(self.root)
        changed = []
        def interleave(sql):
            if sql.startswith('BEGIN') and not changed:
                changed.append(True)
                with other:
                    other.execute("UPDATE jobs SET state='retry'")
        self.db.set_trace_callback(interleave)
        try:
            with self.db:
                batch_store.close_finished(self.db, Client.account)
            self.assertTrue(changed)
            self.assertEqual(self.db.execute("SELECT state FROM curation_batches").fetchone()[0], 'open')
        finally:
            self.db.set_trace_callback(None)
            other.close()
