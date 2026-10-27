"""Revision fingerprints fence real mutations without loading large receipt columns."""
import sqlite3
from unittest import TestCase
from x_curator import proof_revisions
from x_curator.row_fingerprint import row_digest


class ProofRevisionTests(TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.db.execute('CREATE TABLE facts(id TEXT PRIMARY KEY, body BLOB)')
        self.db.execute('INSERT INTO facts VALUES (?,?)',('one',b'x'*10000))
        self.db.commit()
        proof_revisions.prepare(self.db)

    def test_update_delete_and_reused_rowid_change_the_fingerprint(self):
        query=('SELECT * FROM facts WHERE id=?',('one',))
        before=proof_revisions.stamp(self.db,query)
        epoch=proof_revisions.epoch(self.db)
        self.assertNotEqual(before,row_digest(self.db.execute(*query)))
        self.db.execute("UPDATE facts SET body=X'79'")
        after=proof_revisions.stamp(self.db,query)
        self.assertNotEqual(epoch,proof_revisions.epoch(self.db))
        self.assertNotEqual(before,after)
        self.db.execute('DELETE FROM facts')
        self.assertNotEqual(after,proof_revisions.stamp(self.db,query))
        self.db.execute("INSERT INTO facts VALUES ('one',X'79')")
        self.assertNotEqual(after,proof_revisions.stamp(self.db,query))
        self.db.rollback()
        self.assertEqual(epoch,proof_revisions.epoch(self.db))
        self.assertEqual(before,proof_revisions.stamp(self.db,query))

    def test_journal_cannot_be_rewound_replaced_or_deleted(self):
        for sql in ("UPDATE proof_rows SET version=version-1",'DELETE FROM proof_rows',
                    "INSERT OR REPLACE INTO proof_rows SELECT * FROM proof_rows"):
            with self.assertRaises(sqlite3.IntegrityError):
                self.db.execute(sql)

    def test_empty_results_and_unsupported_queries_stay_fenced(self):
        query=('SELECT body FROM facts WHERE id=?',('missing',))
        before=proof_revisions.stamp(self.db,query)
        self.db.execute("INSERT INTO facts VALUES ('missing',X'00')")
        self.assertNotEqual(before,proof_revisions.stamp(self.db,query))
        for sql in ('SELECT count(*) FROM facts','SELECT * FROM facts LIMIT 1',
                    'SELECT f.* FROM facts f JOIN facts g ON f.id=g.id'):
            self.assertEqual(proof_revisions.stamp(self.db,(sql,())),row_digest(self.db.execute(sql)))

    def test_dropped_tracking_trigger_cannot_bless_changed_bytes(self):
        query=('SELECT * FROM facts',())
        proof_revisions.stamp(self.db,query)
        self.db.execute('DROP TRIGGER proof_facts_update')
        self.db.execute("UPDATE facts SET body=X'01'")
        with self.assertRaises(ValueError):
            proof_revisions.stamp(self.db,query)
        with self.assertRaises(ValueError):
            proof_revisions.prepare(self.db)

    def test_untracked_tables_disable_the_global_epoch_shortcut(self):
        self.db.execute('CREATE TABLE external(value TEXT PRIMARY KEY) WITHOUT ROWID')
        proof_revisions.prepare(self.db)
        self.assertIsNone(proof_revisions.epoch(self.db))
