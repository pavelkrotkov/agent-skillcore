"""The default two-phase executor must not retain native logs in its output JSON."""
import json
from unittest.mock import patch

from x_quick_phase_fixtures import PhaseCase
from x_curator import compact_history, wiki_store
from x_curator.publication_audit import verify_publication


class CompactPhaseTests(PhaseCase):
    def setUp(self):
        super().setUp()
        self.assertIsNotNone(self.run_phases())
        wiki_store.initialize(self.db)
        self.db.commit()

    def test_embedded_events_rollout_and_prompt_are_replaced_by_compact_facts(self):
        before = self.db.execute("SELECT output,output_sha FROM executions WHERE role='factcheck_evidence'").fetchone()
        original = json.loads(before['output'])
        compact_history.run(self.db, self.root, apply=True)
        after = self.db.execute("SELECT output,output_sha,log FROM executions WHERE role='factcheck_evidence'").fetchone()
        receipt = json.loads(after['output'])
        proof = receipt['input_proof']
        self.assertEqual(proof['format'], 'compact-input-proof/v1')
        self.assertFalse({'events', 'rollout', 'prompt'} & proof.keys())
        self.assertEqual(after['output_sha'], before['output_sha'])
        self.assertIsNone(after['log'])
        self.assertEqual(receipt['ended'], original['ended'])
        self.assertLess(len(after['output']), len(before['output']) // 2)
        row = self.db.execute('SELECT * FROM publications').fetchone()
        with patch('x_curator.model_trace.native', side_effect=AssertionError('native replay')):
            self.assertIsNotNone(verify_publication(self.db, self.root, row))

    def test_changed_compact_evidence_receipt_is_rejected(self):
        compact_history.run(self.db, self.root, apply=True)
        with self.db:
            self.db.execute("UPDATE executions SET output='{}' WHERE role='factcheck_evidence'")
        row = self.db.execute('SELECT * FROM publications').fetchone()
        with self.assertRaisesRegex(ValueError, 'dependency changed'):
            verify_publication(self.db, self.root, row)
