import json

from x_deep_fixtures import DeepCase
from x_native_search_fixtures import NativeCase
from x_curator import deep_review
from x_curator.receipts import encoded


class NativeDeepCase(DeepCase):
    def native_approval(self):
        self.authorize()
        self.deep()
        account = self.db.execute('SELECT account FROM research_permissions').fetchone()[0]
        self.value = deep_review.prepare(self.db, account, 'synthetic-chat', self.approval, native=True)
        self.references = [i['reference'] for i in json.loads(self.value['payload'])['review']]
        self.assertIn('12-query target', self.value['message'])
        self.observe()
        self.reply('research ' + self.references[0], identity='explicit-native-human')
        self.approval = self.db.execute('SELECT id FROM research_permissions WHERE consumed IS NULL').fetchone()[0]
        self.search_log = encoded({'type': 'item.completed', 'item': {'id': 'native-deep-search',
            'type': 'web_search', 'action': {'type': 'search', 'queries': ['synthetic ' + str(i) for i in range(13)]},
            'results': [{'url': 'https://example.test/release'}]}}) + b'\n'
        self.tools = []
        self.checker = lambda request: NativeCase.checker(self, request)
