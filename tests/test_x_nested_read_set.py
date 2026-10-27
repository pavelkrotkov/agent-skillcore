"""Precommit baselines retain nested proofs, while activation rereads every dependency."""
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from x_curator import read_set, row_fingerprint
from x_curator.read_set import ChangedDependencies, ReadSet


class NestedReadSetTests(TestCase):
    def test_nested_query_digest_is_not_recomputed_until_activation(self):
        with sqlite3.connect(':memory:') as db:
            db.execute('CREATE TABLE facts (body TEXT)')
            db.execute("INSERT INTO facts VALUES ('original')")
            outer = ReadSet(db)
            inner = ReadSet(outer)
            inner.execute('SELECT body FROM facts').fetchall()
            expected = inner.fingerprint()
            inner.verify(expected)
            with patch.object(row_fingerprint, 'row_digest', wraps=row_fingerprint.row_digest) as digest:
                stamp = outer.captured()
            self.assertEqual(digest.call_count, 0)
            self.assertEqual(stamp, expected)
            db.execute("UPDATE facts SET body='changed'")
            with self.assertRaises(ChangedDependencies):
                outer.verify(stamp)

    def test_empty_nested_query_and_outer_only_query_stay_fenced(self):
        with sqlite3.connect(':memory:') as db:
            db.execute('CREATE TABLE facts (body TEXT)')
            outer = ReadSet(db)
            inner = ReadSet(outer)
            inner.execute('SELECT body FROM facts').fetchall()
            inner.fingerprint()
            outer.execute('SELECT count(*) FROM facts').fetchone()
            with patch.object(row_fingerprint, 'row_digest', wraps=row_fingerprint.row_digest) as digest:
                stamp = outer.captured()
            self.assertEqual(digest.call_count, 1)
            db.execute("INSERT INTO facts VALUES ('new')")
            with self.assertRaises(ChangedDependencies):
                outer.verify(stamp)

    def test_file_changed_before_baseline_is_rejected_even_with_identical_stat(self):
        with TemporaryDirectory() as directory, sqlite3.connect(':memory:') as db:
            root = Path(directory)
            path = root/'proof.txt'
            path.write_bytes(b'original')
            prior = path.stat()
            outer = ReadSet(db)
            inner = ReadSet(outer)
            inner.read_file(root, 'proof.txt')
            inner.fingerprint()
            path.write_bytes(b'tampered')
            os.utime(path, ns=(prior.st_atime_ns, prior.st_mtime_ns))
            with patch.object(read_set, 'read_file', wraps=read_set.read_file) as read:
                stamp = outer.captured()
            self.assertEqual(read.call_count, 0)
            with self.assertRaises(ChangedDependencies):
                outer.verify(stamp)
