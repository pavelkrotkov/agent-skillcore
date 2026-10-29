"""Compact approval migration regression checks."""
from unittest.mock import patch
from x_compact_fixtures import CompactCase
from x_curator import compact_history, audit_reuse, compact_seal, wiki_inputs
from x_curator.publication_audit import audit as audit_publications
from x_curator.proof_mode import MaintenanceRequired, audit


class CompacthistoryTests(CompactCase):
    def test_preview_is_read_only_and_does_not_create_proof_store_or_key(self):
        before = self.db.execute('SELECT sum(length(log)) FROM executions').fetchone()[0]
        result = compact_history.preview(self.root)
        self.assertGreater(result['transcript_bytes'], 0)
        self.assertFalse(compact_seal.present(self.db))
        self.assertEqual(before, self.db.execute('SELECT sum(length(log)) FROM executions').fetchone()[0])


    def test_approvals_and_mapping_survive_removal_cache_loss_and_full_audit(self):
        report = compact_history.run(self.db, self.root, apply=True)
        self.assertEqual((report['publications'], report['mappings']), (1, 1))
        self.assertEqual(self.db.execute('SELECT count(*) FROM executions WHERE log IS NOT NULL').fetchone()[0], 0)
        self.assertIsNone(self.db.execute('SELECT proposal FROM wiki_runs').fetchone()[0])
        audit_reuse._CACHE.clear()
        for path in (self.root / 'audit-memos').glob('*.memo'):
            path.unlink()
        with audit(), patch('x_curator.model_trace.native', side_effect=AssertionError('raw replay')):
            self.assertEqual(self.verified()[0], self.packet)
            mappings = wiki_inputs.mappings(self.db, self.sources)
        self.assertTrue(mappings)


    def test_idempotent_compaction_leaves_canonical_records_and_attempt_budgets(self):
        before = self.db.execute('SELECT sum(attempts),sum(max_attempts) FROM jobs').fetchone()
        compact_history.run(self.db, self.root, apply=True)
        again = compact_history.run(self.db, self.root, apply=True)
        self.assertEqual(again['transcript_bytes'], 0)
        self.assertEqual(tuple(before), tuple(self.db.execute('SELECT sum(attempts),sum(max_attempts) FROM jobs').fetchone()))
        self.assertEqual(self.db.execute('SELECT count(*) FROM captures').fetchone()[0], len(self.evidence['captures']))
