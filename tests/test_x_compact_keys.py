"""Lost permanent proof keys require restoration, never silent replacement."""
from x_compact_fixtures import CompactCase
from x_curator import compact_history, compact_seal
from x_curator.proof_mode import MaintenanceRequired


class CompactKeyTests(CompactCase):
    def test_missing_key_is_not_recreated_by_verification(self):
        compact_history.run(self.db, self.root, apply=True)
        key = self.root / 'audit-memos/key'
        key.unlink()
        with self.assertRaisesRegex(MaintenanceRequired, 'key unavailable'):
            self.verified()
        self.assertFalse(key.exists())
        self.assertEqual(self.db.execute('SELECT state FROM publications').fetchone()[0], 'published')

    def test_later_proof_write_cannot_recreate_a_lost_canonical_key(self):
        compact_history.run(self.db, self.root, apply=True)
        identity = ('publication', self.publication)
        record = compact_seal.read(self.db, self.root, identity)
        key = self.root / 'audit-memos/key'
        key.unlink()
        with self.assertRaisesRegex(MaintenanceRequired, 'key unavailable'):
            compact_seal.write(self.db, self.root, ('publication', 'another'), record, active=1)
        self.assertFalse(key.exists())

    def test_later_proof_write_rejects_a_mismatched_existing_key(self):
        compact_history.run(self.db, self.root, apply=True)
        identity = ('publication', self.publication)
        record = compact_seal.read(self.db, self.root, identity)
        (self.root / 'audit-memos/key').write_bytes(b'x' * 32)
        with self.assertRaisesRegex(MaintenanceRequired, 'signature'):
            compact_seal.write(self.db, self.root, ('publication', 'another'), record, active=1)
