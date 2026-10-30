"""Keep signed authority mandatory while reusing unchanged source verification work."""
from unittest.mock import patch

from x_compact_fixtures import CompactCase
from x_curator import compact_history, compact_validation
from x_curator.proof_mode import MaintenanceRequired


class CompactReuseTests(CompactCase):
    def test_unchanged_reads_do_not_reload_all_acquired_source_bytes(self):
        compact_history.run(self.db, self.root, apply=True)
        with patch.object(compact_validation, 'publication', wraps=compact_validation.publication) as verify:
            self.verified()
            self.verified()
        self.assertEqual(verify.call_count, 1)

    def test_cached_result_cannot_bypass_a_damaged_canonical_signature(self):
        compact_history.run(self.db, self.root, apply=True)
        self.verified()
        with self.db:
            self.db.execute("UPDATE compact_approvals SET signature=X'00' WHERE kind='publication'")
        with self.assertRaises(MaintenanceRequired):
            self.verified()
