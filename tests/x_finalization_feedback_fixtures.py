import json

from test_x_quick_final import FinalCase
from x_curator import quick_mcp
from x_curator.receipts import digest


class FeedbackCase(FinalCase):
    def checker(self, request):
        root = self.root / 'runs' / self.token
        root.mkdir(parents=True)
        (root / (digest(request) + '.jsonl')).write_bytes(self.search_log)
        self.at = self.start + 50
        read = quick_mcp.call(self.db, self.token, 'read', {'source': 'https://example.test/release'})
        capture = json.loads(read['content'][0]['text'])['capture']
        decision = self.packet_for(capture)
        if self.subjective:
            decision['checks'][0]['status'] = 'subjective'
            decision['packet']['claims'][0]['kind'] = 'recommendation'
        bad = json.loads(json.dumps(decision))
        wrong = capture[:20] + 'deadbeef'
        bad['checks'][0]['sources'][0]['capture'] = wrong
        bad['packet']['claims'][0]['citations'][0]['capture'] = wrong
        self.at = self.start + 70
        rejected = quick_mcp.call(self.db, self.token, 'validate', {'decision': bad})
        self.assertTrue(rejected['isError'])
        self.assertIn('Unknown capture', rejected['content'][0]['text'])
        self.assertIn(capture, rejected['content'][0]['text'])
        self.assertNotIn('final_answer', rejected['content'][0]['text'])
        self.at = self.start + 85
        accepted = quick_mcp.call(self.db, self.token, 'validate', {'decision': decision})
        self.assertFalse(accepted['isError'], accepted)
        response = json.loads(accepted['content'][0]['text'])
        self.assertEqual(response['final_answer'], dict(format=request['final_format'], decision_sha=digest(decision)))
        self.assertIn('final response now', response['next_action'])
        self.at = self.start + 100
        return self.terminal(request, decision, [read, rejected, accepted], self.search_log)
