import json
import sqlite3
import unittest

from x_fixtures import SCRIPTS
from x_curator import execution_snapshot
from x_curator.row_fingerprint import row_digest


class ExecutionSnapshotTests(unittest.TestCase):
    def test_guard_names_changed_metadata_without_leaking_receipts_or_weakening_hash(self):
        with sqlite3.connect(':memory:') as db:
            self.addCleanup(db.close)
            db.execute('CREATE TABLE executions(model TEXT, input TEXT, log BLOB, started REAL)')
            db.execute('CREATE TABLE proof_rows(table_name TEXT,row_id INTEGER,version INTEGER)')
            values = ('synthetic-model', 'PRIVATE BODY', b'PRIVATE LOG', 1.25)
            db.execute('INSERT INTO executions VALUES(?,?,?,?)', values)
            db.execute("INSERT INTO proof_rows VALUES('executions',1,3)")
            db.commit()
            before = execution_snapshot.capture(db)
            self.assertFalse(db.in_transaction)
            self.assertEqual(before['rows']['1']['sha256'], row_digest((values,)).hex())
            self.assertFalse(execution_snapshot.differences(before, execution_snapshot.capture(db)))
            db.execute('INSERT INTO executions VALUES(?,?,?,?)', values)
            db.commit()
            self.assertFalse(execution_snapshot.differences(before, execution_snapshot.capture(db)))
            db.execute("UPDATE executions SET model='different-model'")
            db.execute('UPDATE proof_rows SET version=4')
            db.commit()
            changed = execution_snapshot.differences(before, execution_snapshot.capture(db))
            self.assertEqual(changed['1']['columns'], ['model'])
            self.assertEqual(changed['1']['before']['revision'], 3)
            self.assertEqual(changed['1']['after']['revision'], 4)
            for secret in ('PRIVATE BODY', 'PRIVATE LOG', 'synthetic-model', 'different-model'):
                self.assertNotIn(secret, json.dumps(changed))
            db.execute('UPDATE executions SET input=?', (b'PRIVATE BODY',))
            in_transaction = execution_snapshot.capture(db)
            self.assertTrue(db.in_transaction)
            self.assertTrue(in_transaction['transaction_open'])
            typed = execution_snapshot.differences(before, in_transaction)
            self.assertEqual(typed['1']['columns'], ['input', 'model'])
            self.assertIn('transaction_open', typed['metadata'])
            db.rollback()
            db.execute('DELETE FROM executions')
            db.commit()
            deleted = execution_snapshot.differences(before, execution_snapshot.capture(db))['1']
            self.assertIsNone(deleted['after']['sha256'])
            self.assertIsNone(deleted['after']['revision'])
            self.assertEqual(deleted['columns'],
                             ['input', 'log', 'model', 'started'])
