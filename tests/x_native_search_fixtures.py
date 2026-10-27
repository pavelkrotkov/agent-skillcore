import json

from x_quick_fixtures import QuickCase, native
from x_curator import native_search, quick_mcp, quick_process
from x_curator.receipts import digest, encoded
from unittest.mock import patch


class NativeCase(QuickCase):
    search_mode = native_search.MODE

    def setUp(self):
        super().setUp()
        self.search_log = encoded({'type': 'item.completed', 'item': {
            'id': 'search-1', 'type': 'web_search', 'action': {
                'type': 'search', 'queries': ['synthetic release ' + str(i) for i in range(4)]},
            'results': [{'url': 'https://example.test/release'}]}}) + b'\n'
        self.tools = []

    def checker(self, request):
        root = self.root / 'runs' / self.token
        root.mkdir(parents=True)
        (root / (digest(request) + '.jsonl')).write_bytes(self.search_log)
        read = quick_mcp.call(self.db, self.token, 'read', {'source': 'https://example.test/release'})
        self.assertFalse(read['isError'], read)
        decision = self.modify(self.packet_for(json.loads(read['content'][0]['text'])['capture']))
        self.tools.append(read)
        self.tools.append(quick_mcp.call(self.db, self.token, 'validate', {'decision': decision}))
        return native(request, decision, self.tools, self.search_log)

    def run_check(self):
        with patch('x_curator.quick_web.fetch', self.fetch), patch('x_curator.quick_process.runner', return_value=self.checker):
            return quick_process.research(self.db, self.root, self.client, self.token)
