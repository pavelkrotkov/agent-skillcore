"""Connection-local temporary databases must not invalidate source evidence proofs."""
from contextlib import closing
import sqlite3

from x_compact_fixtures import CompactCase
from x_curator import blobs
from x_curator.read_set import ReadSet


class BlobProofRootTests(CompactCase):
    def test_media_dependency_survives_temp_schema_vacuum_and_reopening(self):
        with closing(sqlite3.connect(self.root / 'curator.sqlite3')) as db:
            identity = blobs.put(db, b'synthetic source media')
            reads = ReadSet(db)
            self.assertEqual(blobs.read(reads, identity), b'synthetic source media')
            expected = reads.fingerprint()
            db.execute('CREATE TEMP TABLE scratch (value TEXT)')
            reads.verify(expected)
            db.execute('VACUUM')
            reads.verify(expected)
            queries, files, metadata = dict(reads.queries), dict(reads.files), dict(reads.metadata)
        with closing(sqlite3.connect(self.root / 'curator.sqlite3')) as reopened:
            reads = ReadSet(reopened)
            reads.queries, reads.files, reads.metadata = queries, files, metadata
            reads.verify(expected)
