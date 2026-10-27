from copy import deepcopy
from unittest.mock import patch, Mock

from x_fixtures import Client, collect, envelope, tweet_entry
from x_publication_fixtures import PublicationCase
from x_curator.acquire import acquire
from x_curator.evidence import bundle
from x_curator.publication import publish
from x_curator.publication_audit import audit
from x_curator.receipts import digest, encoded


def post(entry):
    return entry['content']['itemContent']['tweet_results']['result']


class ArticleRecoveryCase(PublicationCase):
    def setUp(self):
        entry = tweet_entry('1')
        post(entry)['article'] = {'article_results': {'result': {
            'rest_id': '123', 'title': 'Synthetic article', 'metadata': {'modified_at_secs': 10}}}}
        with patch('x_publication_fixtures.tweet_entry', return_value=entry):
            super().setUp()
        self.original = deepcopy(next(iter(self.evidence['captures'].values()))['source']['entry'])
        self.focal = deepcopy(post(self.original))
        self.focal['article']['article_results']['result']['plain_text'] = 'Original full article body.'
        body = encoded(dict(data=self.focal))
        capture = acquire(self.db, self.token, 'https://x.com/i/status/1', lambda _: (200, 'application/json', body, None))
        self.evidence = bundle(self.db, self.token)
        self.packet['bundle_sha'] = digest(self.evidence)
        self.packet['coverage'].append(dict(capture=capture, status='covered', notes='Article context reviewed.'))
        proposal, review = self.approved_executions()
        self.identity = publish(self.db, self.root, self.token, proposal, review)

    def sparse(self):
        current = deepcopy(self.original)
        post(current).pop('article')
        post(current)['grok_analysis_button'] = True
        collect(self.db, Client([(200, envelope([{'type': 'TimelineAddEntries', 'entries': [current]}], 'bookmarks'))]),
                'bookmarks', delay=0, new=True)
        self.assertEqual(audit(self.db, self.root), [self.identity])

    def detail_client(self, focal=None, status=200):
        return Mock(account=Client.account, detail=Mock(return_value=(status, encoded(dict(data=focal or self.focal)))))

    def history(self):
        tables = ('attempts', 'executions', 'captures', 'retrievals', 'publications')
        return {name: [tuple(row) for row in self.db.execute('SELECT * FROM '+name)] for name in tables}
