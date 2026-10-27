import json
from unittest.mock import patch

from test_x_quick_final import FinalCase
from x_curator.model_trace import records
from x_curator.publication_audit import audit
from x_curator.receipts import encoded


def without_timing(log):
    proof = json.loads(log)
    rows = records(proof['rollout'].encode())
    for row in rows:
        payload = row.get('payload', {})
        if payload.get('type') == 'function_call_output':
            output = json.loads(payload['output'])
            output['content'] = output['content'][:1]
            payload['output'] = json.dumps(output)
    proof['rollout'] = '\n'.join(encoded(row).decode() for row in rows) + '\n'
    return encoded(proof)


class TimingProofTests(FinalCase):
    def test_unobserved_controller_timing_cannot_pass_native_proof(self):
        terminal = self.terminal
        with patch.object(self, 'terminal', side_effect=lambda *args: without_timing(terminal(*args))):
            self.assertIsNone(self.run_final())
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
        self.assertIn('tool response absent', self.db.execute('SELECT reason FROM quick_checks').fetchone()[0])

    def test_legacy_single_block_tool_receipts_still_audit(self):
        with patch('x_curator.quick_tool_feedback.append', return_value=None):
            self.assertIsNotNone(self.run_final())
        self.assertEqual(audit(self.db, self.root), [])
        outputs = [json.loads(r[0]) for r in self.db.execute('SELECT output FROM quick_tools')]
        self.assertEqual({len(v['content']) for v in outputs}, {1})
