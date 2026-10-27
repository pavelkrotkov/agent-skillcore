import json
from unittest.mock import Mock, patch

from x_fixtures import Client, CollectionCase, collect, envelope, tweet_entry
from x_quick_fixtures import native
from x_thread_fixtures import post
from x_curator import quick_mcp
from x_curator.worker import work


class ContextCase(CollectionCase):
    def setUp(self):
        super().setUp()
        entry = tweet_entry('1')
        entry['content']['itemContent']['tweet_results']['result']['legacy'] = {'full_text': 'A thread opener.'}
        collect(self.db, Client([(200, envelope([{'type': 'TimelineAddEntries', 'entries': [entry]}]))]), 'likes', delay=0)
        root, continuation = post('1', 'a', '1'), post('2', 'a', '1')
        root['note_tweet'] = {'note_tweet_results': {'result': {'text': 'Complete long note.'}}}
        continuation['legacy']['full_text'] = 'I recommend keeping a notebook.'
        self.posts = [root, continuation, post('3', 'b', '1'), post('4', 'a', '4')]
        self.client = Client([])
        self.request = self.validation = self.token = None

    def run_worker(self, body=None):
        self.client.detail = Mock(return_value=(200, body or json.dumps({'data': self.posts}).encode()))
        with patch('x_curator.quick_process.runner', self.runner), \
                patch('x_curator.research.research', side_effect=AssertionError('deep research forbidden')):
            return work(self.db, self.root, self.client, max_items=1, defer_index=True)

    def runner(self, _db, token):
        self.token = token
        return self.checker

    def checker(self, request):
        self.request = request
        capture = next(k for k, c in request['bundle']['captures'].items() if c.get('focal_id') == '2')
        decision = {'format': 'compact-v1', 'outcome': 'supported', 'reason': 'Attributed recommendation.',
                    'claims': [{'text': 'I recommend keeping a notebook.', 'kind': 'recommendation',
                                'status': 'subjective', 'attribution': 'Thread author', 'limitations': [],
                                'sources': [{'capture': capture, 'quote': 'I recommend keeping a notebook.',
                                             'primary': False, 'credible': False, 'origin': 'Thread author',
                                             'reason': 'Authenticated continuation supports attribution.'}]}]}
        self.validation = quick_mcp.call(self.db, self.token, 'validate', {'decision': decision})
        return native(request, decision, [self.validation])
