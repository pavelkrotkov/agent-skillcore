import json
from copy import deepcopy

from test_x_quick_final import FinalCase
from x_curator import quick_mcp
from x_curator.receipts import digest


def timing(response):
    return json.loads(response['content'][-1]['text'])['timing']


class EarlyCase(FinalCase):
    def checker(self, request):
        root = self.root / 'runs' / self.token
        root.mkdir(parents=True)
        (root / (digest(request) + '.jsonl')).write_bytes(self.search_log)
        self.assertEqual(request['timing']['validation_target_seconds_remaining'], 70)
        self.at = self.start + 60
        read = quick_mcp.call(self.db, self.token, 'read', {'source': 'https://example.test/release'})
        cite = json.loads(read['content'][0]['text'])['capture']
        decision = self.packet_for(cite)
        bad = deepcopy(decision)
        bad['checks'][0]['sources'][0]['quote'] = 'Not present in this source.'
        self.at = self.start + 70
        rejected = quick_mcp.call(self.db, self.token, 'validate', {'decision': bad})
        self.assertTrue(rejected['isError'])
        self.assertIn(cite, rejected['content'][0]['text'])
        self.assertEqual(timing(rejected)['remaining_seconds'], 50)
        self.assertEqual(timing(rejected)['validation_target_seconds_remaining'], 0)
        self.at = self.start + 80
        closed = quick_mcp.call(self.db, self.token, 'read', {'source': 'https://example.test/release'})
        self.assertTrue(closed['isError'])
        self.assertEqual(timing(closed)['read_window_seconds_remaining'], 0)
        self.at = self.start + 90
        accepted = quick_mcp.call(self.db, self.token, 'validate', {'decision': decision})
        self.assertFalse(accepted['isError'], accepted)
        self.assertEqual(timing(accepted)['remaining_seconds'], 30)
        self.at = self.start + 105
        return self.terminal(request, decision, [read, rejected, closed, accepted], self.search_log)
