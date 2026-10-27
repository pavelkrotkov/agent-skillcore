from contextlib import closing
import sqlite3
import unittest

from x_curator.quick_schema import initialize


class ReplacementMigrationTests(unittest.TestCase):
    def test_legacy_rows_survive_migration_and_identity_constraints_remain(self):
        with closing(sqlite3.connect(':memory:')) as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('CREATE TABLE quick_checks(id TEXT PRIMARY KEY)')
            db.executemany('INSERT INTO quick_checks VALUES(?)', [('original',), ('first',)])
            db.execute('''CREATE TABLE quick_recoveries (
                original TEXT PRIMARY KEY REFERENCES quick_checks(id), replacement TEXT UNIQUE NOT NULL,
                account TEXT NOT NULL, source TEXT NOT NULL, created REAL NOT NULL, evidence TEXT NOT NULL,
                review_batch TEXT, UNIQUE(account,source))''')
            first = ('original', 'first', 'account', 'source', 1.0, 'retained approval', 'retained batch')
            db.execute('INSERT INTO quick_recoveries VALUES(?,?,?,?,?,?,?)', first)
            initialize(db)
            initialize(db)
            self.assertEqual(db.execute('SELECT * FROM quick_recoveries').fetchone(), first)
            second = ('first', 'second', 'account', 'source', 2.0, 'new approval', None)
            db.execute('INSERT INTO quick_recoveries VALUES(?,?,?,?,?,?,?)', second)
            self.assertEqual(db.execute('SELECT * FROM quick_recoveries ORDER BY created').fetchall(), [first, second])
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO quick_recoveries VALUES(?,?,?,?,?,?,?)', second)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO quick_recoveries VALUES(?,?,?,?,?,?,?)', ('missing', 'third', 'a', 's', 3, '{}', None))
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
