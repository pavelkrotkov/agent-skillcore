import sqlite3
from unittest import TestCase

from x_curator.read_set import ReadSet, ChangedDependencies
from x_curator.row_fingerprint import row_digest


class ReadSetTests(TestCase):
    def test_raw_scalar_hashing_preserves_types_and_field_and_row_boundaries(self):
        variants = [((b'a', b'bc'),), ((b'ab', b'c'),), (('x',),), ((b'x',),),
                    ((None,),), (('None',),), ((1,),), (('1',),), ((1, 2),), ((1,), (2,))]
        self.assertEqual(len({row_digest(rows) for rows in variants}), len(variants))

    def test_bound_binary_and_nul_parameters_replay_exactly(self):
        with sqlite3.connect(':memory:') as db:
            reads = ReadSet(db)
            parameters = ('a\0b', b'\0binary', 1.25, None)
            self.assertEqual(reads.execute('SELECT ?,?,?,?', parameters).fetchone(), parameters)
            reads.verify(reads.fingerprint())
            self.assertEqual(next(iter(reads.queries))[1], parameters)

    def test_empty_results_are_dependencies_and_writes_are_rejected_before_execution(self):
        with sqlite3.connect(':memory:') as db:
            db.execute('CREATE TABLE values_seen (id INTEGER PRIMARY KEY, body BLOB)')
            reads = ReadSet(db)
            self.assertIsNone(reads.execute('SELECT body FROM values_seen WHERE id=?', (1,)).fetchone())
            stamp = reads.fingerprint()
            db.execute('INSERT INTO values_seen VALUES (?,?)', (1, b'new'))
            with self.assertRaises(ChangedDependencies):
                reads.verify(stamp)
            with self.assertRaisesRegex(ValueError, 'only recorded reads'):
                reads.execute('DELETE FROM values_seen')
            self.assertEqual(db.execute('SELECT count(*) FROM values_seen').fetchone()[0], 1)
