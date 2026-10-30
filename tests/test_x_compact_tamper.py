"""Compact approval migration regression checks."""
from unittest.mock import patch
from x_compact_fixtures import CompactCase
from x_curator import compact_history, audit_reuse, compact_seal, wiki_inputs
from x_curator.publication_audit import audit as audit_publications
from x_curator.proof_mode import MaintenanceRequired, audit


class CompacttamperTests(CompactCase):
    def test_corrupt_seal_requires_maintenance_without_invalidating_or_retrying(self):
        compact_history.run(self.db, self.root, apply=True)
        with self.db:
            self.db.execute("UPDATE compact_approvals SET body=X'00' WHERE kind='publication'")
        with self.assertRaises(MaintenanceRequired):
            audit_publications(self.db, self.root)
        self.assertEqual(self.db.execute('SELECT state FROM publications').fetchone()[0], 'published')
        self.assertEqual(self.db.execute('SELECT count(*) FROM publication_audit_failures').fetchone()[0], 0)


    def test_missing_seal_cannot_fall_back_to_an_optional_memo(self):
        compact_history.run(self.db, self.root, apply=True)
        with self.db:
            self.db.execute("DELETE FROM compact_approvals WHERE kind='publication'")
        with self.assertRaisesRegex(MaintenanceRequired, 'missing'):
            self.verified()


    def test_wrong_controller_key_fails_closed(self):
        compact_history.run(self.db, self.root, apply=True)
        (self.root / 'audit-memos/key').write_bytes(b'z' * 32)
        with self.assertRaisesRegex(MaintenanceRequired, 'signature'):
            self.verified()


    def test_changed_model_hash_is_detected_without_retaining_the_transcript(self):
        compact_history.run(self.db, self.root, apply=True)
        with self.db:
            self.db.execute("UPDATE executions SET log_sha='changed'")
        with self.assertRaisesRegex(ValueError, 'dependency changed'):
            self.verified()


    def test_changed_capture_cannot_reuse_the_signed_approval(self):
        compact_history.run(self.db, self.root, apply=True)
        with self.db:
            self.db.execute("UPDATE captures SET payload='{}'")
        with self.assertRaises(ValueError):
            self.verified()


    def test_source_file_tampering_is_still_detected(self):
        compact_history.run(self.db, self.root, apply=True)
        path = self.db.execute('SELECT path FROM publications').fetchone()[0]
        (self.root / path).write_text('changed source page')
        with self.assertRaises(ValueError):
            self.verified()
