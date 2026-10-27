import json
from unittest.mock import patch
from x_quick_phase_fixtures import PhaseCase
from x_curator import model_events, quick_proof
from x_curator.receipts import digest, encoded
from x_curator.storage import sha256


class PhaseProofTests(PhaseCase):
    def test_unobserved_acquisition_output_cannot_be_invented_by_handoff(self):
        def omitted(receipt):
            proof = receipt['input_proof']
            proof['rollout'] = '\n'.join(line for line in proof['rollout'].split('\n') if 'function_call_output' not in line)
            return receipt
        self.cutoff_change = omitted
        self.assertIsNone(self.run_phases())
        self.assertEqual(self.final_calls, 0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)

    def test_native_search_in_final_phase_invalidates_publication(self):
        from x_quick_fixtures import native
        def searched(request, decision, responses, searches=b''):
            return native(request, decision, responses, self.search_log if request['phase']['name'] == 'final' else searches)
        with patch('x_quick_phase_final.native', side_effect=searched):
            self.assertIsNone(self.run_phases())
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)

    def test_completed_evidence_phase_cannot_be_relabelled_as_a_publication_execution(self):
        from x_quick_fixtures import native
        self.assertIsNotNone(self.run_phases())
        evidence = json.loads(self.db.execute("SELECT input FROM executions WHERE role='factcheck'").fetchone()[0])['bundle']
        row = self.db.execute("SELECT id FROM executions WHERE role='factcheck_evidence'").fetchone()
        log = native(self.initial, self.decision, [self.read], self.search_log)
        session, output = model_events.result(log)
        with self.db:
            self.db.execute("UPDATE executions SET role='synthetic_other' WHERE role='factcheck'")
            self.db.execute("UPDATE executions SET role='factcheck',session=?,output=?,output_sha=?,log=?,log_sha=? WHERE id=?",
                            (session, encoded(output).decode(), digest(output), log, sha256(log), row['id']))
        with self.assertRaisesRegex(ValueError, 'not a publication verdict'):
            quick_proof.decision_proof(self.db, self.token, row['id'], evidence)
