"""Schema upgrades accelerate authentic proof reads without changing their results."""
from x_publication_fixtures import PublicationCase
from x_curator import receipts
from x_curator.publication import publish
from x_curator.publication_audit import verify_publication
from x_curator.storage import open_store


def records(db):
    return [line for line in db.iterdump() if line.startswith('INSERT INTO')]


def query_plan(db, query):
    return " ".join(row[3] for row in db.execute('EXPLAIN QUERY PLAN ' + query))


class ProofIndexTests(PublicationCase):
    def test_existing_corpus_upgrade_preserves_proofs_and_rejects_tampering(self):
        self.db.execute('DROP INDEX IF EXISTS selections_id_run')
        self.db.execute('DROP INDEX IF EXISTS captures_token_id')
        proposal, review = self.approved_executions()
        identity = publish(self.db, self.root, self.token, proposal, review)
        row = self.db.execute('SELECT * FROM publications WHERE id=?', (identity,)).fetchone()
        before = verify_publication(self.db, self.root, row)
        snapshot = records(self.db)
        self.db.close()
        self.db = open_store(self.root)
        receipts.initialize(self.db)
        receipts.initialize(self.db)
        queries = []
        self.db.set_trace_callback(queries.append)
        self.assertEqual(verify_publication(self.db, self.root, row), before)
        self.db.set_trace_callback(None)
        self.assertEqual(records(self.db), snapshot)
        selection = next(q for q in queries if q.startswith('SELECT s.*'))
        captures = next(q for q in queries if q.startswith('SELECT * FROM captures WHERE token='))
        self.assertIn('SEARCH s USING INDEX selections_id_run', query_plan(self.db, selection))
        self.assertIn('SEARCH captures USING INDEX captures_token_id', query_plan(self.db, captures))
        with self.db:
            self.db.execute("UPDATE responses SET sha256='tampered'")
        with self.assertRaisesRegex(ValueError, 'tampered acquisition receipt'):
            verify_publication(self.db, self.root, row)
