"""Retained-conflict proofs stay exact while avoiding whole-history scans."""
import sqlite3
from contextlib import closing
from unittest import TestCase

from x_curator import retrieval_store, wiki_store, x_response_conflicts


class RetrievalIndexTests(TestCase):
    def test_wiki_upgrade_indexes_conflict_fence_without_changing_history(self):
        with closing(sqlite3.connect(':memory:')) as db:
            db.row_factory = sqlite3.Row
            retrieval_store.initialize(db)
            db.execute('DROP INDEX IF EXISTS retrievals_source_finished')
            db.executemany('INSERT INTO retrievals VALUES (?,?,?,?,?,?,?,?,?,?)',
                           ((str(i), 'token', 'account', str(i), 'https://x.com/i/status/2',
                             0, 2, 404, None, None) for i in range(5000)))
            evidence = dict(account='account', source='1')
            queries = []
            db.set_trace_callback(queries.append)
            self.assertTrue(x_response_conflicts.superseded(db, evidence, '2', 1, 3, {}))
            query = queries[-1]
            snapshot = db.execute('SELECT * FROM retrievals ORDER BY id').fetchall()
            wiki_store.initialize(db)
            wiki_store.initialize(db)
            self.assertEqual(db.execute('SELECT * FROM retrievals ORDER BY id').fetchall(), snapshot)
            plan = ' '.join(r[3] for r in db.execute('EXPLAIN QUERY PLAN ' + query))
            self.assertIn('SEARCH retrievals USING INDEX retrievals_source_finished', plan)
            self.assertTrue(x_response_conflicts.superseded(db, evidence, '2', 1, 3, {}))
            self.assertFalse(x_response_conflicts.superseded(db, evidence, '2', 2, 3, {}))
