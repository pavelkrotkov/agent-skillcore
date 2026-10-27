import json

import test_x_quick_flow
from x_quick_fixtures import QuickCase
from x_curator.model_trace import records
from x_curator.publication_audit import audit
from x_curator.quick_tool_proof import tool_output
from x_curator.receipts import encoded


def framed(log, clipped):
    proof = json.loads(log)
    rows = records(proof['rollout'].encode())
    values = [json.loads(r['payload']['output']) for r in filter(tool_output, rows)]
    if clipped:
        values[-1]['content'][0]['text'] = values[-1]['content'][0]['text'][:-1]
    text = 'Script completed\nOutput:\n' + '\n'.join(json.dumps({'result': v}) for v in values)
    rows = [r for r in rows if r['payload'].get('type') != 'function_call_output']
    rows.insert(-1, {'type': 'response_item', 'payload': {'type': 'custom_tool_call_output',
                     'output': [{'type': 'input_text', 'text': text}]}})
    proof['rollout'] = '\n'.join(json.dumps(r) for r in rows)
    return encoded(proof)


class ToolOutputFramesTests(QuickCase):
    run_check = test_x_quick_flow.QuickFlowTests.run_check

    def check(self, clipped=False):
        original = self.checker
        self.checker = lambda request: framed(original(request), clipped)
        return self.run_check()

    def test_complete_json_line_frames_publish_and_replay(self):
        identity = self.check()
        self.assertIsNotNone(identity)
        self.assertEqual(audit(self.db, self.root), [])

    def test_clipped_frame_cannot_publish(self):
        self.assertIsNone(self.check(clipped=True))
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'awaiting_review')
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
