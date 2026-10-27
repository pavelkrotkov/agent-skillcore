from unittest.mock import patch

from x_fixtures import Client, CollectionCase, collect, envelope, tweet_entry
from x_quick_fixtures import native
from x_curator import quick_mcp
from x_curator.worker import work


class LinkedCase(CollectionCase):
    urls = ['https://example.test/release']

    def setUp(self):
        super().setUp()
        entry = tweet_entry('1')
        tweet = entry['content']['itemContent']['tweet_results']['result']
        tweet['legacy'] = {'full_text': 'I recommend the tool.',
                           'entities': {'urls': [{'expanded_url': url} for url in self.urls]}}
        collect(self.db, Client([(200, envelope([{'type': 'TimelineAddEntries', 'entries': [entry]}]))]), 'likes', delay=0)
        self.token = self.validation = self.request = None
        self.decision = self.supported

    def fetch(self, _url):
        return 200, 'text/plain', b'The tool was released in 2025. Original release announcement.', None

    def runner(self, _db, token):
        self.token = token
        return self.checker

    def checker(self, request):
        self.request = request
        decision = self.decision(request)
        self.validation = quick_mcp.call(self.db, self.token, 'validate', {'decision': decision})
        return native(request, decision, [self.validation])

    def run_worker(self, runner=None):
        with patch('x_curator.quick_web.fetch', self.fetch), patch('x_curator.quick_process.runner', runner or self.runner):
            return work(self.db, self.root, Client([]), max_items=1)

    def ids(self, request):
        captures = request['bundle']['captures']
        return (next(k for k, v in captures.items() if v['kind'] == kind) for kind in ('selection', 'text'))

    def source(self, capture, quote, status='supported', primary=True):
        return {'text': quote, 'kind': 'fact', 'attribution': 'Synthetic source', 'limitations': [], 'status': status,
                'sources': [{'capture': capture, 'quote': quote, 'primary': primary, 'credible': primary,
                             'origin': 'Synthetic source', 'reason': 'Direct captured evidence.'}]}

    def supported(self, request):
        selection, linked = self.ids(request)
        opinion = self.source(selection, 'I recommend the tool.', 'subjective', False)
        opinion.update(kind='recommendation', attribution='Liked post author')
        return {'format': 'compact-v1', 'outcome': 'supported', 'reason': 'Linked evidence supports the useful note.',
                'claims': [self.source(linked, 'The tool was released in 2025.'), opinion]}
