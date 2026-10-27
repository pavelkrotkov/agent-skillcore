from x_fixtures import CollectionCase
from x_curator.audit_reuse import cached
from x_curator import blobs


class AuditDependencyTests(CollectionCase):
    def test_absent_sql_result_remains_a_dependency(self):
        with self.db:
            self.db.execute('CREATE TABLE observed_dependencies (value INTEGER)')
        def absent(reads):
            row = reads.execute('SELECT value FROM observed_dependencies').fetchone()
            return None if row is None else tuple(row)
        self.assertIsNone(cached(self.db, self.root, ('absence', 1), absent))
        with self.db:
            self.db.execute('INSERT INTO observed_dependencies VALUES (1)')
        self.assertEqual(cached(self.db, self.root, ('absence', 1), absent), (1,))

    def test_changed_acquisition_bytes_reject_cached_proof(self):
        identity = blobs.put(self.db, b'retained evidence')
        read = lambda reads: blobs.read(reads, identity)
        self.assertEqual(cached(self.db, self.root, ('blob', identity), read), b'retained evidence')
        (self.root / 'blobs' / identity).write_bytes(b'altered! evidence')
        with self.assertRaisesRegex(ValueError, 'tampered acquisition'):
            cached(self.db, self.root, ('blob', identity), read)
