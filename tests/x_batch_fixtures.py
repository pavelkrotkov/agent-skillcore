from unittest.mock import patch

from x_quick_fixtures import QuickCase, native
from x_fixtures import Client, collect, envelope, tweet_entry
from x_curator import batch_queue, batch_report
from x_curator.leases import fail
from x_curator.worker import work


class BatchCase(QuickCase):
    def setUp(self):
        super().setUp()
        fail(self.db, self.token, 'Synthetic fixture ready for normal dispatch', 0)

    def add_items(self, count):
        entries = [tweet_entry(str(i)) for i in range(2, count + 1)]
        for entry in entries:
            entry['content']['itemContent']['tweet_results']['result']['legacy'] = {'full_text': 'Synthetic evidence.'}
        collect(self.db, Client([(200, envelope([{'type': 'TimelineAddEntries', 'entries': entries}]))]), 'likes', new=True, delay=0)

    def model(self, db, token):
        self.token = token
        return self.checker

    def run_batch(self, limit=100, defer_index=False):
        with patch('x_curator.quick_web.fetch', self.fetch), patch('x_curator.quick_search.fetch', self.fetch), patch('x_curator.quick_process.runner', self.model), patch('x_curator.research.research', side_effect=AssertionError('deep work forbidden')):
            return work(self.db, self.root, Client([]), max_items=limit, defer_index=defer_index)

    def pending(self, request):
        return native(request, {'outcome': 'inconclusive', 'reason': 'The release year remains unresolved.', 'central': ['f1'],
            'checks': [{'id': 'f1', 'text': 'The tool was released in 2025.', 'status': 'inconclusive', 'sources': []}]}, [])
