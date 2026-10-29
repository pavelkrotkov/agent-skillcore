"""Lost permanent proof keys require restoration, never silent replacement."""
from x_compact_fixtures import CompactCase
from x_curator import compact_history
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
